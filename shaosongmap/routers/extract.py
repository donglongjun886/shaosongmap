"""/api/v1/extract 路由：SSE 流式提取管道。

路由层仅负责 SSE 序列化和 HTTP 传输，管道逻辑委托给 services.pipeline。
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from shaosongmap.config import limiter
from shaosongmap.schemas import ExtractRequest
from shaosongmap.services.pipeline import run_extract_pipeline
from shaosongmap.utils import sse_event

router = APIRouter(prefix='/api/v1')


@router.post('/extract')
@limiter.limit('5/minute')
async def extract_campaign(body: ExtractRequest, request: Request):
    """从战役文本中提取结构化数据并返回地图要素（SSE 流式）。

    通过 Server-Sent Events 推送管道各阶段进度，
    最终以 result 事件返回完整数据。
    """
    if not body.text.strip():
        raise HTTPException(
            status_code=422,
            detail={'error': {'code': 'INVALID_INPUT', 'message': '战役文本不能为空'}},
        )

    async def event_stream():
        for stage in run_extract_pipeline(body.text, body.dynasty, body.mode):
            yield sse_event(stage.event, stage.data)

    return StreamingResponse(
        event_stream(),
        media_type='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
            'Connection': 'keep-alive',
        },
    )
