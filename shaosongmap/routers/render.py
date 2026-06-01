"""/api/render 路由：用户修正数据后重新渲染地图（仅地名 Point，不产路线）。"""

from __future__ import annotations

import asyncio
import logging
import uuid

from fastapi import APIRouter, HTTPException

from shaosongmap.geocoder import geocode
from shaosongmap.models import Boundary, GeoEntityExtract, PersonPlace, Place
from shaosongmap.schemas import ExtractResponse, RenderRequest
from shaosongmap.services.geo import DYNASTY_YEARS
from shaosongmap.services.geojson import make_geojson

logger = logging.getLogger(__name__)

router = APIRouter(prefix='/api/v1')


@router.post('/render', response_model=ExtractResponse)
async def render_modified(request: RenderRequest):
    """接收用户修正后的提取数据，跳过 LLM 提取，直接 geocode + GeoJSON。

    用于前端可编辑面板的「重新渲染」功能。
    仅生成地名 Point 要素，不产出行军路线（LineString）。
    """
    logger.info(
        '渲染请求: event=%s, %d 地名, %d 人物地点关联, scale=%s',
        request.event_name,
        len(request.places),
        len(request.person_places),
        request.scale,
    )

    # 重建 Pydantic 模型
    try:
        boundaries = [Boundary(**b) for b in request.boundaries]
        places = [Place(**p) for p in request.places]
        person_places = [PersonPlace(**pp) for pp in request.person_places]
    except Exception as e:
        logger.warning('渲染请求数据格式错误: %s', e, exc_info=True)
        raise HTTPException(
            status_code=400,
            detail={
                'error': {'code': 'INVALID_FORMAT', 'message': '数据格式错误', 'detail': str(e)}
            },
        ) from e

    extract = GeoEntityExtract(
        event_name=request.event_name,
        dynasty=request.dynasty,
        boundaries=boundaries,
        places=places,
        person_places=person_places,
        scale=request.scale,  # type: ignore[arg-type]  # RenderRequest.scale 为 str|None，运行时 Pydantic 校验
    )

    # Geocode
    dyn_beg, dyn_end = None, None
    if request.dynasty and request.dynasty in DYNASTY_YEARS:
        dyn_beg, dyn_end = DYNASTY_YEARS[request.dynasty]

    try:
        features = await asyncio.to_thread(
            geocode,
            extract.places,
            context_text='',
            dynasty_beg_yr=dyn_beg,
            dynasty_end_yr=dyn_end,
        )
    except Exception as e:
        logger.error('地理编码失败: %s', e, exc_info=True)
        raise HTTPException(
            status_code=422,
            detail={
                'error': {'code': 'GEOCODE_FAILED', 'message': '地名匹配失败', 'detail': str(e)}
            },
        ) from e

    geojson = make_geojson(features)

    return ExtractResponse(
        extract_id=uuid.uuid4().hex[:12],
        event_name=extract.event_name,
        dynasty=request.dynasty,
        boundaries=[b.model_dump() for b in extract.boundaries],
        person_places=[pp.model_dump() for pp in extract.person_places],
        places=[p.model_dump() for p in extract.places],
        features=[f.model_dump() for f in features],
        geojson=geojson,
        scale=extract.scale,
    )
