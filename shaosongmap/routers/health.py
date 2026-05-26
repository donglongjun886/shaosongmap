"""健康检查端点：供 k8s liveness/readiness probe 使用。"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Request
from starlette.responses import JSONResponse

router = APIRouter(tags=['health'])

logger = logging.getLogger(__name__)


@router.get('/health')
async def health():
    """Liveness 探活：进程是否存活。始终返回 200。"""
    return {'status': 'ok'}


@router.get('/ready')
async def ready(request: Request):
    """Readiness 就绪检查：配置和 OCR 模型是否就绪。"""
    from shaosongmap.config import settings

    if settings is None or not settings.deepseek_api_key:
        return JSONResponse(
            status_code=503,
            content={'status': 'not_ready', 'reason': '配置未加载或 deepseek_api_key 缺失'},
        )

    ocr_ready = getattr(request.app.state, 'ocr_ready', False)
    if not ocr_ready:
        return JSONResponse(
            status_code=503,
            content={'status': 'not_ready', 'reason': 'OCR 模型尚未加载'},
        )

    return {'status': 'ready'}
