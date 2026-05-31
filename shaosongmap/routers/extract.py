"""/api/v1/extract 路由：SSE 流式提取管道。

路由层仅负责 SSE 序列化和 HTTP 传输，管道逻辑委托给 services.pipeline。
"""

from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from shaosongmap.config import limiter
from shaosongmap.schemas import ExtractRequest
from shaosongmap.services.pipeline import PipelineStage, run_extract_pipeline
from shaosongmap.utils import sse_event

logger = logging.getLogger(__name__)

router = APIRouter(prefix='/api/v1')


@router.post('/extract')
@limiter.limit('5/minute')
async def extract_campaign(body: ExtractRequest, request: Request):
    """从战役文本中提取结构化数据并返回地图要素（SSE 流式）。

    通过 Server-Sent Events 推送管道各阶段进度，
    最终以 result 事件返回完整数据。
    """
    if not body.text.strip():
        logger.warning('提取请求文本为空')
        raise HTTPException(
            status_code=422,
            detail={'error': {'code': 'INVALID_INPUT', 'message': '战役文本不能为空'}},
        )

    logger.info('提取请求: 文本长度=%d', len(body.text))

    async def event_stream():
        queue: asyncio.Queue[PipelineStage | None] = asyncio.Queue()
        loop = asyncio.get_running_loop()
        exc_info: Exception | None = None

        def _run_pipeline() -> None:
            nonlocal exc_info
            try:
                for stage in run_extract_pipeline(body.text, body.dynasty):
                    loop.call_soon_threadsafe(queue.put_nowait, stage)
            except Exception as exc:
                exc_info = exc
            finally:
                loop.call_soon_threadsafe(queue.put_nowait, None)

        fut = loop.run_in_executor(None, _run_pipeline)

        while True:
            item = await queue.get()
            if item is None:
                break
            yield sse_event(item.event, item.data)

        await fut
        if exc_info is not None:
            raise exc_info

    return StreamingResponse(
        event_stream(),
        media_type='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
            'Connection': 'keep-alive',
        },
    )
