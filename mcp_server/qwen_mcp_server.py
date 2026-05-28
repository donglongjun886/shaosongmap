#!/usr/bin/env python3
"""MCP Server：将 Qwen 多模态 + DeepSeek 审查能力暴露为 Claude Code 工具。

Local-Only Architecture —— 此 Server 与 Claude Code 运行在同一台机器，通过本地文件路径传递截图。
若未来需容器化或云端部署，analyze_ui / run_e2e_test 的 image_path 参数需重构为 OSS URL。

工具列表:
  analyze_ui              — 截图诊断 (Qwen-VL-Max)
  generate_frontend       — 看图生成视觉骨架代码 (Qwen-VL-Max)
  review_code             — 代码审查 (DeepSeek-reasoner)
  run_e2e_test            — 端到端视觉自测 (Playwright → Qwen-VL-Max)

前端开发"皮/骨"分工:
  Qwen-VL-Max 负责"皮"——HTML结构/CSS布局/古风配色/Canvas兵牌基础绘制
  DeepSeek 主控负责"骨"——贝塞尔曲线/MapLibre坐标变换/缩放同步/状态机

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
            return p
        except ValueError:
            continue
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


def _prepare_image(path: Path, max_edge: int = 1280, quality: int = 85) -> tuple[str, str]:
    """读取图片，缩到最长边 max_edge，转 JPEG，返回 (mime_type, data_url)。

    大幅减小体积（3.4MB → ~250KB），Qwen-VL 内部本身会缩放，不影响诊断效果。
    """
    img = Image.open(path)
    w, h = img.size
    if max(w, h) > max_edge:
        ratio = max_edge / max(w, h)
        img = img.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)
    if img.mode in ('RGBA', 'P'):
        img = img.convert('RGB')
    buf = io.BytesIO()
    img.save(buf, format='JPEG', quality=quality, optimize=True)
    b64 = base64.b64encode(buf.getvalue()).decode()
    return 'image/jpeg', f'data:image/jpeg;base64,{b64}'


# ── 错误处理 ──────────────────────────────────────────────
def _transient_retry(func, max_retries: int = 1):
    """透明重试装饰器：502/超时等瞬态错误自动重试 1 次。"""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        last_exc = None
        for attempt in range(max_retries + 1):
            try:
                return func(*args, **kwargs)
            except Exception as exc:
                last_exc = exc
                msg = str(exc).lower()
                is_transient = any(
                    kw in msg for kw in ('timeout', '502', '503', 'connection', 'rate limit')
                )
                if not is_transient or attempt >= max_retries:
                    break
                time.sleep(1.5 * (attempt + 1))
        raise last_exc  # type: ignore[misc]

    return wrapper


def _business_error(msg: str) -> str:
    """返回业务语义错误（不含 traceback），Claude Code 收到后触发 Self-Correction。"""
    return json.dumps(
        {'error': True, 'message': msg, 'action': '模型应据此错误信息决定重试或报告用户'}
    )


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
        _qwen_client = OpenAI(
            api_key=api_key,
            base_url='https://dashscope.aliyuncs.com/compatible-mode/v1',
            timeout=30.0,
        )
    return _qwen_client


def _get_deepseek_client():
    global _deepseek_client
    if _deepseek_client is None:
        from openai import OpenAI

        api_key = os.environ.get('DEEPSEEK_API_KEY', '')
        if not api_key:
            raise RuntimeError('DEEPSEEK_API_KEY 未配置')
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
        return _business_error(f'图片文件未就绪或不存在: {image_path}')

    try:
        mime, data_url = _prepare_image(path)
    except Exception as exc:
        return _business_error(f'图片处理失败: {exc}')

    default_prompt = (
        '请客观描述这张截图的内容。包括：页面整体布局、有哪些 UI 元素、文字内容、颜色、'
        '以及任何明显的视觉问题（如元素重叠、文字截断、错位、报错信息等）。'
    )

    try:
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
        content = resp.choices[0].message.content
        return content.strip() if content else '(模型返回空)'
    except Exception as exc:
        logger.error('analyze_ui API 失败: %s', exc)
        return _business_error(f'Qwen-VL API 调用失败: {exc}')


@mcp.tool()
def review_code() -> str:
    """审查当前工作区未提交的代码变更。调用 DeepSeek-reasoner 深度推理。

    独立于 MCP 也可通过 git hook 或命令行 python scripts/code_review.py 运行。
    """
    script = (PROJECT_ROOT / 'scripts' / 'code_review.py').resolve()
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
            return _business_error(
                f'code_review 执行失败 (rc={result.returncode}): {result.stderr[:300]}'
            )
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        logger.error('review_code 超时')
        return _business_error('代码审查超时（120s），diff 可能过大，建议手动审查或分批提交')
    except Exception as exc:
        logger.error('review_code 异常: %s', exc)
        return _business_error(f'代码审查异常: {exc}')


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
    # selftest.py 依赖 describe.py，两者都在 scripts/ 目录下
    cmd = [sys.executable, str(script)]
    if test_text:
        cmd.append(test_text)
    cmd.extend(['--url', url])

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=180,
            cwd=str(PROJECT_ROOT),
            env={**os.environ},
        )
        # selftest 的输出流式较长，MCP 只返回摘要
        output = result.stdout
        # 提取关键行：程序化检查结果 + 视觉审查结论
        lines = output.splitlines()
        summary_lines = [
            ln
            for ln in lines
            if any(kw in ln for kw in ('✅', '❌', '⚠️', '部队', '时间轴', '视觉', '自测'))
        ]
        summary = '\n'.join(summary_lines[-30:])  # 最多保留 30 行
        if not summary:
            summary = output[-1500:]  # fallback: 最后 1500 字符

        if result.returncode != 0:
            return json.dumps(
                {
                    'status': 'fail',
                    'summary': summary,
                    'stderr': result.stderr[:500],
                },
                ensure_ascii=False,
            )
        return json.dumps(
            {
                'status': 'pass',
                'summary': summary,
            },
            ensure_ascii=False,
        )
    except subprocess.TimeoutExpired:
        logger.error('run_e2e_test 超时')
        return _business_error(
            '端到端自测超时（180s），建议检查服务是否运行，手动执行 python scripts/selftest.py'
        )
    except Exception as exc:
        logger.error('run_e2e_test 异常: %s', exc)
        return _business_error(f'自测异常: {exc}')


@mcp.tool()
@_transient_retry
def generate_frontend(description: str, image_path: str = '', target_file: str = '') -> str:
    """生成前端视觉骨架代码。调用 Qwen-VL-Max，支持截图输入。

    定位：负责"皮"——HTML结构/CSS布局/古风配色/Canvas兵牌基础绘制。
    不负责"骨"——复杂贝塞尔曲线、MapLibre坐标变换、缩放同步、状态机由主控DeepSeek补充。

    Args:
        description: 前端需求描述，应包含组件功能、样式要求、技术约束、现有代码上下文等
        image_path: 可选，参考截图路径（项目目录或 /tmp 下）。传入时Qwen-VL直接看图理解设计意图
        target_file: 可选，目标文件路径（相对于项目根目录，必须在 static/ 下）。
                     为空时仅返回代码不写入文件。
    """

    system_prompt = (
        '你是一位资深前端工程师，专精于 Canvas 2D 渲染、MapLibre GL JS 和 React 18。\n'
        '项目背景：一个历史战役地图可视化应用（ShaosongMap），将《绍宋》等小说的战役文本'
        '转化为古中国风地图。\n\n'
        '你的分工定位（重要）：\n'
        '你负责"画皮"——还原视觉层面：HTML结构、CSS布局、古风配色、字体渲染、'
        'Canvas兵牌/旗帜基础绘制、基础UI交互骨架。\n'
        '你不负责"画骨"——复杂贝塞尔曲线、MapLibre坐标矩阵变换、'
        'Canvas与底图缩放同步、大型状态机 —— 这些留给主控模型DeepSeek后续注入。\n'
        '遇到上述复杂算法时，用占位函数（如 drawArrow_placeholder）或注释标注即可。\n\n'
        '技术约束：\n'
        '- 零构建工具起步，优先使用 vanilla JS ES6 + Canvas API\n'
        '- MapLibre GL JS 4.7.1 为底图库\n'
        '- 古风渲染走 Canvas 2D（毛笔笔触、朱砂印章风格）\n'
        '- React 18 用于 UI 面板（时间轴、图例、工具栏）\n'
        '- 字体：Noto Serif SC\n'
        '- 色彩：古风暖色调（#f5f0e1 背景，#8b4513 棕色系，#c41e3a 朱砂红）\n\n'
        '输出要求：\n'
        '- 生成完整可运行的代码，不要省略细节\n'
        '- 保持与项目现有代码风格一致\n'
        '- 复杂算法用占位函数 + 注释说明意图\n'
        '- 直接输出代码，不要用 markdown 代码块包裹'
    )

    # 构建消息内容
    user_content: list = []

    if image_path:
        img_path = _validate_path(image_path)
        if not _wait_file_ready(img_path):
            return _business_error(f'图片文件未就绪或不存在: {image_path}')
        try:
            mime, data_url = _prepare_image(img_path)
        except Exception as exc:
            return _business_error(f'图片处理失败: {exc}')
        user_content.append({'type': 'image_url', 'image_url': {'url': data_url}})
        user_content.append(
            {
                'type': 'text',
                'text': f'请参考以上截图的设计风格和布局，生成前端代码。需求描述：{description}',
            }
        )
    else:
        user_content.append({'type': 'text', 'text': description})

    try:
        client = _get_qwen_client()
        resp = client.chat.completions.create(
            model='qwen-vl-max',
            messages=[
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_content},
            ],
            max_tokens=8000,
            temperature=0.3,
        )
        code = resp.choices[0].message.content
        if not code:
            return _business_error('Qwen-VL-Max 返回为空')

        result = code.strip()

        # 如果指定了目标文件，写入
        if target_file:
            target = (PROJECT_ROOT / target_file).resolve()
            try:
                target.relative_to((PROJECT_ROOT / 'static').resolve())
            except ValueError:
                return _business_error(f'文件路径越权: {target_file}（仅允许写入 static/ 目录）')
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(result, encoding='utf-8')
            return json.dumps(
                {
                    'status': 'ok',
                    'file': target_file,
                    'size_bytes': len(result),
                    'preview': result[:500],
                },
                ensure_ascii=False,
            )

        return result

    except Exception as exc:
        logger.error('generate_frontend 失败: %s', exc)
        return _business_error(f'Qwen-VL-Max 调用失败: {exc}')


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

# ── 入口 ──────────────────────────────────────────────────
if __name__ == '__main__':
    logging.basicConfig(level=logging.WARNING, format='[qwen-mcp] %(levelname)s: %(message)s')
    mcp.run()
