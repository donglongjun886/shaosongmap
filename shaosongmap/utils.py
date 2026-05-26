"""工具函数：SSE 事件序列化等。"""

from __future__ import annotations

import json


def sse_event(event: str, data: dict) -> str:
    """构建一条 SSE 格式的事件字符串。"""
    return f'event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n'
