#!/usr/bin/env python3
"""LLM Code Review — 用 Qwen3.7-Max（思考模式）审查 git diff，输出评审意见。"""

from __future__ import annotations

import logging
import os
import subprocess

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(override=False)

SYSTEM_PROMPT = """你是 ShaosongMap 项目的代码审查员。这是一个 Python 3.10+ (FastAPI + Pydantic) 后端 + Vanilla JS 前端的 solo 开源项目，使用 SSE 流式推送、pytest 测试、ruff + mypy 质量工具。

## 架构约定

- 后端分层：接口层只做参数校验和转发，业务逻辑在独立 service 层，领域模型与传输模型分离
- 配置集中管理（避免散落 os.getenv），重量资源在应用启动时预加载
- 异步函数内禁止同步阻塞调用；SSE 端点需防止阻塞事件循环
- 地图图层声明式管理（source 创建一次，数据原地更新）

## 技术决策原则

项目追求最小可维护复杂度。判断一个建议是否值得提出的标准：
- 是否解决了当前 diff 中实际存在的问题？（而非"业界推荐"或"未来可能需要"）
- 引入的复杂度是否小于它解决的问题？
- 方案是否与现有技术栈匹配？（如 Vue 比 React 更适合渐进式改造）

基于以上原则：
- 只有在当前架构确实无法高效解决问题时，才建议引入新技术（框架、数据库等）
- 只有在复杂度增长到明显不可维护时，才建议提取抽象或拆分模块
- 测试建议应针对核心逻辑路径，工具函数或简单胶水代码不强制要求

## ruff 已覆盖——以下问题不要报告

- 代码格式化、导入排序、引号风格、行宽
- 未使用变量/导入、语法错误等基础检测
- 可变默认参数、裸 except 等常见陷阱

## 审查分类

🔴 严重: 逻辑错误、安全漏洞 (XSS/注入/密钥硬编码)、数据丢失 (异常吞没/资源未释放)、架构违规 (异步混用/同步阻塞)

🟡 建议: 性能退化、健壮性不足 (无超时/无重试/无错误处理)、前端内存泄漏/连接未关闭

🟢 风格: 命名不一致、注释过时、代码重复超过 3 次（ruff 能修的不在此列）

## 输出格式

每个问题一行：`文件路径:行号: 级别: 问题描述`
如果没有问题：`✅ 未发现明显问题`
中文输出，简洁直接。"""

MAX_DIFF_LINES = 600

logger = logging.getLogger(__name__)


def get_diff() -> str:
    """获取当前 push / PR 的 diff。"""
    try:
        event_name = os.environ.get('GITHUB_EVENT_NAME', '')
        if event_name == 'pull_request':
            base = os.environ.get('GITHUB_BASE_SHA', 'HEAD~1')
            head = os.environ.get('GITHUB_HEAD_SHA', 'HEAD')
        else:
            base = os.environ.get('GITHUB_EVENT_BEFORE', '')
            head = os.environ.get('GITHUB_EVENT_AFTER', 'HEAD')
            if not base or base == '0000000000000000000000000000000000000000':
                base = 'HEAD~1'

        diff_range = f'{base}..{head}'

        result = subprocess.run(
            ['git', 'diff', diff_range, '--', ':(exclude)uv.lock', ':(exclude)openspec/'],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            logger.warning('git diff 失败 (rc=%d): %s', result.returncode, result.stderr)
            return ''
        return result.stdout
    except subprocess.SubprocessError as exc:
        logger.warning('git diff 执行异常: %s', exc)
        return ''


def _build_review_messages(diff: str) -> list[dict]:
    """根据 diff 规模构建不同深度的审查指令。"""
    truncated_lines = diff.splitlines()
    if len(truncated_lines) > MAX_DIFF_LINES:
        truncated_diff = '\n'.join(truncated_lines[:MAX_DIFF_LINES])
        truncated_diff += '\n\n... (diff 过长已截断)'
    else:
        truncated_diff = diff

    line_count = len(truncated_lines)
    if line_count < 200:
        focus = '全类别审查（逻辑、安全、性能、架构、风格、测试），报告所有发现的问题。'
    elif line_count < 500:
        focus = '重点审查逻辑错误、安全漏洞和架构违规。风格问题只报告明显的（如硬编码密钥、未处理错误），不报告命名/注释类问题。'
    else:
        focus = '仅审查严重问题：逻辑错误和安全漏洞。其他类别一律跳过。'

    return [
        {'role': 'system', 'content': SYSTEM_PROMPT},
        {'role': 'user', 'content': f'{focus}\n\n审查以下 diff:\n{truncated_diff}'},
    ]


def review(diff: str) -> str:
    """调用 Qwen3.7-Max（思考模式）审查 diff。"""
    if not diff.strip():
        return '✅ 无代码变更，跳过审查'

    api_key = os.environ.get('DASHSCOPE_API_KEY', '')
    if not api_key:
        return '⚠️ 未配置 DASHSCOPE_API_KEY，跳过审查'

    client = OpenAI(
        api_key=api_key,
        base_url='https://dashscope.aliyuncs.com/compatible-mode/v1',
    )

    messages = _build_review_messages(diff)

    try:
        response = client.chat.completions.create(
            model='qwen3.7-max',
            messages=messages,
            extra_body={
                'enable_thinking': True,
                'thinking_budget': 5000,
            },
            max_tokens=2000,
            temperature=0.1,
        )
        return response.choices[0].message.content or '（模型返回为空）'
    except Exception as exc:
        return f'⚠️ 审查 API 调用失败: {exc}'


def main() -> None:
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    diff = get_diff()
    print(f'审查范围: {len(diff)} 字符\n')
    print(review(diff))


if __name__ == '__main__':
    main()
