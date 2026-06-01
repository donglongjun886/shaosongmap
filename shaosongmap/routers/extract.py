"""/api/v1/extract 路由：单次请求/响应提取管道。

路由层仅负责 HTTP 传输，管道逻辑委托给 services.pipeline。
"""

from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, HTTPException, Request

from shaosongmap.config import limiter
from shaosongmap.schemas import ExtractRequest, ExtractResponse
from shaosongmap.services.pipeline import run_extract_pipeline

logger = logging.getLogger(__name__)

router = APIRouter(prefix='/api/v1')


@router.post('/extract', response_model=ExtractResponse)
@limiter.limit('5/minute')
async def extract_geo_entities(body: ExtractRequest, request: Request):
    """从历史文本中提取地理实体数据并返回地图要素（单次请求/响应）。

    在一次 HTTP 请求中完成：LLM 提取 → 地理编码 → GeoJSON 构建。
    """
    if not body.text.strip():
        logger.warning('提取请求文本为空')
        raise HTTPException(
            status_code=422,
            detail={'error': {'code': 'INVALID_INPUT', 'message': '历史文本不能为空'}},
        )

    logger.info('提取请求: 文本长度=%d', len(body.text))

    try:
        result = await asyncio.to_thread(run_extract_pipeline, body.text, body.dynasty)
    except ValueError as e:
        logger.error('提取管道失败: %s', e)
        raise HTTPException(
            status_code=422,
            detail={'error': {'code': 'EXTRACT_FAILED', 'message': str(e)}},
        ) from e
    except Exception as e:
        logger.exception('提取管道内部错误')
        raise HTTPException(
            status_code=500,
            detail={'error': {'code': 'INTERNAL_ERROR', 'message': '服务器内部错误，请稍后重试'}},
        ) from e

    return ExtractResponse(**result)
