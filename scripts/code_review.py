#!/usr/bin/env python3
"""LLM Code Review — 用 Qwen3-Max（思考模式）审查 git diff，输出评审意见。"""

from __future__ import annotations

import os
import subprocess

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

SYSTEM_PROMPT = """你是一位资深 Python 代码审查员。请审查下面的 git diff。

审查要点：
1. **逻辑错误**：边界条件遗漏、状态不一致、控制流缺陷、异常处理缺失
2. **安全漏洞**：注入风险、敏感信息泄露、不安全函数调用（shell=True 等）
3. **性能问题**：不必要的循环、内存浪费、阻塞调用、冗余 I/O
4. **代码风格**：违反 PEP8、不符合项目规范（单引号、行宽 100、中文注释）
5. **测试缺失**：新增逻辑是否缺少对应的测试覆盖

输出格式：
- 每个问题一行：`文件路径:行号: 严重级别: 问题描述`
- 严重级别：🔴严重 🟡建议 🟢风格
- 如果没有发现问题，输出 "✅ 未发现明显问题"
- 用中文输出，简洁直接，不要输出推理过程"""

MAX_DIFF_CHARS = 20_000  # 约 5000 token，留足思考预算


def get_diff() -> str:
    """获取当前 push 的 diff。CI 中用 before/after SHA，本地用 HEAD~1。"""
    try:
        before = os.environ.get('GITHUB_EVENT_BEFORE', '')
        after = os.environ.get('GITHUB_EVENT_AFTER', 'HEAD')

        if before and before != '0000000000000000000000000000000000000000':
            diff_range = f'{before}..{after}'
        else:
            diff_range = 'HEAD~1..HEAD'

        result = subprocess.run(
            ['git', 'diff', diff_range, '--', ':(exclude)uv.lock', ':(exclude)openspec/'],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.stdout
    except Exception:
        return ''


def review(diff: str) -> str:
    """调用 Qwen3-Max（思考模式）审查 diff。"""
    if not diff.strip():
        return '✅ 无代码变更，跳过审查'

    api_key = os.environ.get('DASHSCOPE_API_KEY', '')
    if not api_key:
        return '⚠️ 未配置 DASHSCOPE_API_KEY，跳过审查'

    client = OpenAI(
        api_key=api_key,
        base_url='https://dashscope.aliyuncs.com/compatible-mode/v1',
    )

    if len(diff) > MAX_DIFF_CHARS:
        diff = diff[:MAX_DIFF_CHARS] + '\n\n... (diff 过长已截断)'

    try:
        response = client.chat.completions.create(
            model='qwen3-max',
            messages=[
                {'role': 'system', 'content': SYSTEM_PROMPT},
                {'role': 'user', 'content': diff},
            ],
            extra_body={
                'enable_thinking': True,
                'thinking_budget': 4000,
            },
            max_tokens=2000,
            temperature=0.1,
        )
        return response.choices[0].message.content or '（模型返回为空）'
    except Exception as exc:
        return f'⚠️ 审查 API 调用失败: {exc}'


def main() -> None:
    diff = get_diff()
    print(f'审查范围: {len(diff)} 字符\n')
    print(review(diff))


if __name__ == '__main__':
    main()
