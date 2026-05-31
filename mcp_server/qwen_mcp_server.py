#!/usr/bin/env python3
"""MCP Server：将 Qwen 多模态 + DeepSeek 审查能力暴露为 Claude Code 工具。

Local-Only Architecture —— 此 Server 与 Claude Code 运行在同一台机器，通过本地文件路径传递截图。
若未来需容器化或云端部署，analyze_ui / run_e2e_test 的 image_path 参数需重构为 OSS URL。

工具列表:
  analyze_ui              — 截图诊断 / 设计参数提取 (Qwen-VL-Max)
  review_design           — 设计方案审查 (Qwen3.7-Max 文本)
  review_code             — 代码审查 (DeepSeek-reasoner)
  run_e2e_test            — 端到端视觉自测 (Playwright → Qwen-VL-Max)

新协作分工（2026-05-28 更新）:
  视觉设计：人 + Excalidraw → roughjs 参数 → THEME_CONFIG
  前端实现：DeepSeek主控 — Canvas 渲染器、坐标变换、状态机
  CSS/布局：现有代码库 + 增量修改
  审查链：
    analyze_ui (Qwen-VL-Max)     — 截图诊断 / 设计参数校对
    review_design (Qwen3.7-Max)  — 方案逻辑审计
    review_code (DeepSeek-reasoner) — 代码异源审查
    run_e2e_test (Playwright+Qwen-VL) — 自动化自测

安全设计:
  - 路径白名单：只允许读取项目目录、/tmp、系统临时目录
  - 文件完整性：读取前轮询确保文件写入完成
  - 错误降噪：只返回业务语义，原始 traceback 写日志
  - 透明重试：502/超时在工具层静默重试 1 次
"""

from __future__ import annotations

import atexit
import base64
import contextlib
import functools
import io
import json
import logging
import logging.handlers
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from PIL import Image

load_dotenv(override=False)

logger = logging.getLogger('qwen-mcp')

# ── 路径安全 ──────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
_ALLOWED_ROOTS = {
    PROJECT_ROOT.resolve(),
    Path('/tmp').resolve(),
    Path(tempfile.gettempdir()).resolve(),
}


def _validate_path(path: str) -> Path:
    """校验文件路径在白名单内，防止 LLM 幻觉读取敏感文件。"""
    p = Path(path).resolve()
    for root in _ALLOWED_ROOTS:
        try:
            p.relative_to(root)
            logger.info('路径校验通过: %s (root=%s)', p, root)
            return p
        except ValueError:
            continue
    logger.warning('路径越权: %s (不在白名单内)', p)
    raise PermissionError(f'路径越权: {path}（不在白名单 {_ALLOWED_ROOTS} 内）')


def _wait_file_ready(path: Path, max_wait: float = 0.5) -> bool:
    """轮询等待文件写入完成（解决 Playwright 半截文件问题）。"""
    if not path.exists():
        return False
    start = time.monotonic()
    last_size = -1
    stable_count = 0
    while time.monotonic() - start < max_wait:
        try:
            cur_size = path.stat().st_size
        except OSError:
            time.sleep(0.05)
            continue
        if cur_size == last_size and cur_size > 0:
            stable_count += 1
            if stable_count >= 2:
                return True
        else:
            stable_count = 0
            last_size = cur_size
        time.sleep(0.1)
    return path.stat().st_size > 0


def _prepare_image(path: Path, max_edge: int = 1280, quality: int = 75) -> tuple[str, str]:
    """读取图片，缩到最长边 max_edge，转 JPEG，返回 (mime_type, data_url)。

    quality=75 截图足够 Qwen-VL 识别，比 85 省 30-40% 体积。
    去掉 optimize=True，对截图性价比低（省 5-10% 体积但编码慢 2-3x）。
    """
    logger.info('开始处理图片: %s (max_edge=%d, quality=%d)', path.name, max_edge, quality)
    img = Image.open(path)
    w, h = img.size
    original_size = (w, h)
    if max(w, h) > max_edge:
        ratio = max_edge / max(w, h)
        img = img.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)
        logger.info('图片已缩放: %dx%d -> %dx%d', w, h, img.size[0], img.size[1])
    if img.mode in ('RGBA', 'P'):
        img = img.convert('RGB')
    buf = io.BytesIO()
    img.save(buf, format='JPEG', quality=quality)
    b64 = base64.b64encode(buf.getvalue()).decode()
    logger.info(
        '图片处理完成: %s %dx%d -> %dx%d, jpeg_q=%d, b64_len=%d',
        path.name,
        original_size[0],
        original_size[1],
        img.size[0],
        img.size[1],
        quality,
        len(b64),
    )
    return 'image/jpeg', f'data:image/jpeg;base64,{b64}'


# ── 错误处理 ──────────────────────────────────────────────
def _transient_retry(func, max_retries: int = 1):
    """透明重试装饰器：502/超时等瞬态错误自动重试 1 次。

    重试耗尽后返回 _business_error 而非抛出异常，确保 MCP 工具始终返回字符串。
    被装饰函数不应自行捕获 API 异常——让异常穿透到装饰器触发重试。
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        last_exc = None
        for attempt in range(max_retries + 1):
            try:
                logger.info('调用 %s (attempt=%d/%d)', func.__name__, attempt + 1, max_retries + 1)
                result = func(*args, **kwargs)
                logger.info('%s 调用成功', func.__name__)
                return result
            except Exception as exc:
                last_exc = exc
                msg = str(exc).lower()
                is_transient = any(
                    kw in msg for kw in ('timeout', '502', '503', 'connection', 'rate limit')
                )
                if not is_transient or attempt >= max_retries:
                    break
                logger.warning('瞬态错误重试 %d/%d: %s', attempt + 1, max_retries, exc)
                time.sleep(1.5 * (attempt + 1))
        logger.error('%s 调用失败（已重试 %d 次）: %s', func.__name__, max_retries, last_exc)
        return _business_error(f'{func.__name__} 调用失败: {last_exc}')

    return wrapper


def _business_error(msg: str) -> str:
    """返回业务语义错误（不含 traceback），Claude Code 收到后触发 Self-Correction。"""
    return json.dumps(
        {'error': True, 'message': msg, 'action': '模型应据此错误信息决定重试或报告用户'}
    )


_MAX_INPUT_CHARS = 80000


def _validate_input_length(text: str, label: str) -> str | None:
    """校验输入长度，超限返回错误 JSON 字符串，否则返回 None。"""
    if not text or not text.strip():
        logger.warning('%s: 输入为空', label)
        return _business_error(f'{label}不能为空')
    if len(text) > _MAX_INPUT_CHARS:
        logger.warning('%s: 输入过长 (%d > %d)', label, len(text), _MAX_INPUT_CHARS)
        return _business_error(f'{label}过长（{len(text)}字符），请拆分后分批审查')
    return None


def _safe_api_content(resp, func_name: str) -> str:
    """安全提取 API 响应文本：检查 choices 判空 + finish_reason 截断提示。"""
    if not resp.choices:
        logger.warning('%s: API 返回空 choices（可能安全审核拦截）', func_name)
        return _business_error('模型未返回有效结果，可能触发了安全审核')
    choice = resp.choices[0]
    message = choice.message
    content = message.content.strip() if message and message.content else ''
    if not content:
        return '(模型返回空)'
    if choice.finish_reason == 'length':
        logger.warning('%s: 输出被截断 (finish_reason=length)', func_name)
        content += '\n\n[警告：审查意见因达到 max_tokens 限制被截断，请缩小输入或增加 max_tokens]'
    return content


def _call_qwen_text_review(
    system_prompt: str,
    user_content: str,
    tool_name: str,
    model: str = 'qwen3.7-max',
    max_tokens: int = 4000,
) -> str:
    """调用 Qwen 文本模型做审查，返回提取后的文本内容。

    review_design 和 review_snippet 共享的底层调用逻辑。
    """
    logger.info('%s: 调用 %s (content_len=%d)', tool_name, model, len(user_content))
    client = _get_qwen_client()
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_content},
        ],
        max_tokens=max_tokens,
        temperature=0.3,
    )
    result = _safe_api_content(resp, tool_name)
    logger.info('%s: 完成 (result_len=%d)', tool_name, len(result))
    return result


# ── API 客户端（惰性初始化） ──────────────────────────────
_qwen_client = None
_deepseek_client = None


def _get_qwen_client():
    global _qwen_client
    if _qwen_client is None:
        from openai import OpenAI

        api_key = os.environ.get('DASHSCOPE_API_KEY', '')
        if not api_key:
            raise RuntimeError('DASHSCOPE_API_KEY 未配置')
        logger.info('初始化 Qwen 客户端 (base_url=dashscope)')
        _qwen_client = OpenAI(
            api_key=api_key,
            base_url='https://dashscope.aliyuncs.com/compatible-mode/v1',
            timeout=120.0,
        )
    return _qwen_client


def _get_deepseek_client():
    global _deepseek_client
    if _deepseek_client is None:
        from openai import OpenAI

        api_key = os.environ.get('DEEPSEEK_API_KEY', '')
        if not api_key:
            raise RuntimeError('DEEPSEEK_API_KEY 未配置')
        logger.info('初始化 DeepSeek 客户端 (base_url=api.deepseek.com)')
        _deepseek_client = OpenAI(
            api_key=api_key,
            base_url='https://api.deepseek.com',
            timeout=60.0,
        )
    return _deepseek_client


# ── MCP Server ────────────────────────────────────────────

mcp = FastMCP('qwen-tools')


@mcp.tool()
@_transient_retry
def analyze_ui(image_path: str, question: str = '') -> str:
    """分析 UI 截图，提取设计参数或检查视觉问题。调用 Qwen-VL-Max。

    Args:
        image_path: 截图本地绝对路径（必须在项目目录或 /tmp 下）
        question: 具体分析问题。为空时默认全面扫描布局/元素/颜色/缺陷
    """
    path = _validate_path(image_path)
    if not _wait_file_ready(path):
        logger.warning('analyze_ui: 图片未就绪 %s', image_path)
        return _business_error(f'图片文件未就绪或不存在: {image_path}')

    try:
        mime, data_url = _prepare_image(path)
    except Exception as exc:
        logger.error('analyze_ui: 图片处理失败 %s: %s', image_path, exc)
        return _business_error(f'图片处理失败: {exc}')

    default_prompt = (
        '请客观描述这张截图的内容。包括：页面整体布局、有哪些 UI 元素、文字内容、颜色、'
        '以及任何明显的视觉问题（如元素重叠、文字截断、错位、报错信息等）。'
    )

    logger.info(
        'analyze_ui: 调用 Qwen-VL-Max (image=%s, question_len=%d)',
        path.name,
        len(question),
    )
    client = _get_qwen_client()
    resp = client.chat.completions.create(
        model='qwen-vl-max',
        messages=[
            {
                'role': 'user',
                'content': [
                    {'type': 'image_url', 'image_url': {'url': data_url}},
                    {'type': 'text', 'text': question or default_prompt},
                ],
            }
        ],
        max_tokens=2000,
        temperature=0.3,
    )
    result = _safe_api_content(resp, 'analyze_ui')
    logger.info('analyze_ui: 完成 (result_len=%d)', len(result))
    return result


@mcp.tool()
def review_code() -> str:
    """审查当前工作区未提交的代码变更。调用 DeepSeek-reasoner 深度推理。

    独立于 MCP 也可通过 git hook 或命令行 python scripts/code_review.py 运行。
    """
    script = (PROJECT_ROOT / 'scripts' / 'code_review.py').resolve()
    logger.info('review_code: 开始审查 (script=%s)', script)
    try:
        result = subprocess.run(
            [sys.executable, str(script), '--format', 'json'],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(PROJECT_ROOT),
            env={**os.environ},
        )
        if result.returncode != 0:
            logger.error(
                'review_code: 失败 rc=%d stderr=%s', result.returncode, result.stderr[:200]
            )
            return _business_error(
                f'code_review 执行失败 (rc={result.returncode}): {result.stderr[:300]}'
            )
        logger.info('review_code: 完成 (output_len=%d)', len(result.stdout))
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        logger.error('review_code: 超时')
        return _business_error('代码审查超时（120s），diff 可能过大，建议手动审查或分批提交')
    except Exception as exc:
        logger.error('review_code: 异常 %s', exc)
        return _business_error(f'代码审查异常: {exc}')


def _extract_selftest_summary(output: str) -> str:
    """从 selftest 流式输出中提取关键摘要行，最多保留 30 行。"""
    keywords = ('✅', '❌', '⚠️', '部队', '时间轴', '视觉', '自测')
    summary_lines = [ln for ln in output.splitlines() if any(kw in ln for kw in keywords)]
    summary = '\n'.join(summary_lines[-30:])
    return summary if summary else output[-1500:]


def _build_selftest_result(status: str, summary: str, stderr: str = '') -> str:
    """构建 e2e 自测的 JSON 返回结果。"""
    payload: dict = {'status': status, 'summary': summary}
    if stderr:
        payload['stderr'] = stderr[:500]
    return json.dumps(payload, ensure_ascii=False)


@mcp.tool()
def run_e2e_test(url: str = 'http://localhost:8000', test_text: str = '') -> str:
    """运行前端端到端自测：Playwright 截图 → 程序化检查 → Qwen-VL 视觉验证。

    Args:
        url: 应用地址，默认 http://localhost:8000
        test_text: 测试用的战役文本，为空使用内置默认文本

    Returns:
        JSON: {"status": "pass"|"fail", "checks": {...}, "visual_issues": [...], "screenshot": "..."}
    """
    script = (PROJECT_ROOT / 'scripts' / 'selftest.py').resolve()
    cmd = [sys.executable, str(script)]
    if test_text:
        cmd.append(test_text)
    cmd.extend(['--url', url])

    logger.info('run_e2e_test: 开始 (url=%s, test_text_len=%d)', url, len(test_text))
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=180,
            cwd=str(PROJECT_ROOT),
            env={**os.environ},
        )
        summary = _extract_selftest_summary(result.stdout)
        if result.returncode != 0:
            logger.warning('run_e2e_test: 失败 rc=%d', result.returncode)
            return _build_selftest_result('fail', summary, result.stderr)
        logger.info('run_e2e_test: 完成 (status=pass)')
        return _build_selftest_result('pass', summary)
    except subprocess.TimeoutExpired:
        logger.error('run_e2e_test: 超时 (180s)')
        return _business_error(
            '端到端自测超时（180s），建议检查服务是否运行，手动执行 python scripts/selftest.py'
        )
    except Exception as exc:
        logger.error('run_e2e_test: 异常 %s', exc)
        return _business_error(f'自测异常: {exc}')


# generate_frontend 工具已移除（2026-05-28）
# 原因：Excalidraw + roughjs 替代了 Qwen-VL-Max 的"画皮"能力
# 视觉设计新流程：Excalidraw 手绘 → 导出 roughjs 参数 → 写入 THEME_CONFIG → 代码复用
# analyze_ui 仍保留用于截图诊断和设计参数提取


@mcp.tool()
@_transient_retry
def review_design(design_text: str, context: str = '') -> str:
    """审查设计方案，挑逻辑漏洞、边界问题、性能隐患和改进建议。调用 Qwen3.7-Max 文本模型。

    定位：DeepSeek 出方案 → Qwen3.7-Max 审方案 → DeepSeek 根据意见改进。

    Args:
        design_text: 设计方案描述（OpenSpec design.md 内容、架构图描述、算法思路等）
        context: 可选，项目背景/现有代码约束/已知权衡等补充上下文

    Returns:
        审查意见：问题列表、风险点、改进建议
    """
    if err := _validate_input_length(design_text, '设计方案'):
        return err

    system_prompt = (
        '你是一位资深软件架构师。审查设计方案，找出逻辑漏洞、边界遗漏、性能隐患和安全风险。'
        '每个问题标注严重程度（致命/严重/建议），说明根因并给出改进方向。用中文，直接说重点。'
    )

    user_parts = [f'请审查以下设计方案：\n\n<design>\n{design_text}\n</design>']
    context = (context or '').strip()
    if context:
        user_parts.append(f'\n项目背景/补充上下文：\n<context>\n{context}\n</context>')

    return _call_qwen_text_review(system_prompt, '\n'.join(user_parts), 'review_design')


@mcp.tool()
@_transient_retry
def review_snippet(code_snippet: str, question: str = '') -> str:
    """审查指定代码片段，排查 bug 或逻辑问题。调用 Qwen3.7-Max 文本模型。

    与 review_code（基于 git diff 全量审查）不同，本工具接收任意代码片段 +
    问题描述，做针对性深度分析。

    Args:
        code_snippet: 需要审查的代码片段（函数、文件片段等）
        question: 具体排查方向，如「箭头起点计算为什么偏了」「这段逻辑有死循环吗」

    Returns:
        审查意见：问题列表、根因分析、修复建议
    """
    if err := _validate_input_length(code_snippet, '代码片段'):
        return err
    question = (question or '').strip()
    if question and (err := _validate_input_length(question, '排查方向')):
        return err

    system_prompt = (
        '你是一位资深工程师。审查代码，找出 bug、逻辑错误和边界问题。'
        '每个问题标注严重程度（致命/严重/建议），说明根因并给出修复方案。用中文，直接说重点。'
    )

    user_parts = [f'请审查以下代码片段：\n\n<code>\n{code_snippet}\n</code>']
    if question:
        user_parts.append(f'\n排查方向：<question>\n{question}\n</question>')

    return _call_qwen_text_review(system_prompt, '\n'.join(user_parts), 'review_snippet')


# ── 全局异常兜底 + 资源清理 ──────────────────────────────
_playwright_contexts: list = []


def register_playwright_context(ctx) -> None:
    """注册 Playwright browser context，退出时统一清理。"""
    _playwright_contexts.append(ctx)


@atexit.register
def _cleanup() -> None:
    """优雅退出：清理所有 Playwright browser context。"""
    for ctx in _playwright_contexts:
        with contextlib.suppress(Exception):
            ctx.close()


def _global_exception_handler(exc_type, exc_value, exc_tb):
    """全局异常兜底：捕获未处理异常并转为日志，防止进程僵尸态。"""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_tb)
        return
    logger.critical('未捕获异常: %s: %s', exc_type.__name__, exc_value)


sys.excepthook = _global_exception_handler

# ── 日志落盘 ──────────────────────────────────────────────

_LOG_DIR = PROJECT_ROOT / 'mcp_server'
_LOG_FILE = _LOG_DIR / 'qwen_mcp.log'


def _setup_logging() -> None:
    """配置日志：文件落盘（RotatingFileHandler）+ stderr 双输出。"""
    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    fmt = logging.Formatter(
        '[%(asctime)s][%(filename)s][%(funcName)s:%(lineno)d] %(levelname)s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )
    file_handler = logging.handlers.RotatingFileHandler(
        str(_LOG_FILE), maxBytes=5 * 1024 * 1024, backupCount=3, encoding='utf-8'
    )
    file_handler.setFormatter(fmt)
    file_handler.setLevel(logging.INFO)

    stream_handler = logging.StreamHandler(sys.stderr)
    stream_handler.setFormatter(fmt)
    stream_handler.setLevel(logging.WARNING)

    root_logger = logging.getLogger('qwen-mcp')
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(stream_handler)


# ── 入口 ──────────────────────────────────────────────────
if __name__ == '__main__':
    _setup_logging()
    logger.info('Qwen MCP Server 启动 (project_root=%s)', PROJECT_ROOT)
    mcp.run()
