#!/usr/bin/env python3
"""截图描述工具：用 Qwen-VL 把任意图片转成文字，解决"无法看图"问题。

用法:
    python scripts/describe.py screenshot.png
    python scripts/describe.py screenshot.png "时间轴面板有什么问题？"
"""

from __future__ import annotations

import argparse
import base64
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

BASE_URL = 'https://dashscope.aliyuncs.com/compatible-mode/v1'
MODEL = 'qwen-vl-plus'

DEFAULT_PROMPT = '请客观描述这张截图的内容。包括：页面整体布局、有哪些 UI 元素、文字内容、颜色、以及任何明显的视觉问题（如元素重叠、文字截断、错位、报错信息等）。'


def _encode(path: str) -> str:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f'图片不存在: {path}')
    ext = p.suffix.lower()
    mimes = {
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.webp': 'image/webp',
    }
    mime = mimes.get(ext)
    if not mime:
        raise ValueError(f'不支持格式: {ext}')
    b64 = base64.b64encode(p.read_bytes()).decode()
    return f'data:{mime};base64,{b64}'


def describe(image_path: str, question: str | None = None) -> str:
    api_key = os.getenv('DASHSCOPE_API_KEY', '')
    if not api_key:
        return '错误: 未设置 DASHSCOPE_API_KEY'

    data_url = _encode(image_path)
    prompt = question or DEFAULT_PROMPT

    client = OpenAI(api_key=api_key, base_url=BASE_URL)
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                'role': 'user',
                'content': [
                    {'type': 'image_url', 'image_url': {'url': data_url}},
                    {'type': 'text', 'text': prompt},
                ],
            }
        ],
        max_tokens=2000,
        temperature=0.3,
    )
    content = resp.choices[0].message.content
    return content.strip() if content else '(模型返回空)'


def main() -> None:
    parser = argparse.ArgumentParser(description='截图描述工具')
    parser.add_argument('image', help='图片路径')
    parser.add_argument('question', nargs='?', default=None, help='具体问题（可选）')
    args = parser.parse_args()

    try:
        print(describe(args.image, args.question))
    except (FileNotFoundError, ValueError) as e:
        print(f'错误: {e}', file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
