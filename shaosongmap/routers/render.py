"""/api/render 路由：用户修正数据后重新渲染地图。"""

from __future__ import annotations

import uuid
from typing import cast

from fastapi import APIRouter, HTTPException

from shaosongmap.geocoder import geocode
from shaosongmap.models import CampaignExtract, Faction, MilitaryScale, Place, Route
from shaosongmap.schemas import ExtractResponse, RenderRequest
from shaosongmap.services.geo import _DYNASTY_YEARS
from shaosongmap.services.geojson import build_routes, make_geojson

router = APIRouter()


@router.post('/api/render', response_model=ExtractResponse)
async def render_modified(request: RenderRequest):
    """接收用户修正后的提取数据，跳过 LLM 提取，直接 geocode + GeoJSON。

    用于前端可编辑面板的「重新渲染」功能。
    """

    # 重建 Pydantic 模型
    try:
        factions = [Faction(**f) for f in request.factions]
        places = [Place(**p) for p in request.places]
        routes = [Route(**r) for r in request.routes]
    except Exception as e:
        raise HTTPException(status_code=400, detail=f'数据格式错误: {e}') from e

    campaign = CampaignExtract(
        campaign_name=request.campaign_name,
        factions=factions,
        places=places,
        routes=routes,
        scale=cast(MilitaryScale | None, request.scale),
    )

    # Geocode
    dyn_beg, dyn_end = None, None
    if request.dynasty and request.dynasty in _DYNASTY_YEARS:
        dyn_beg, dyn_end = _DYNASTY_YEARS[request.dynasty]

    try:
        features = geocode(
            campaign.places,
            context_text='',
            dynasty_beg_yr=dyn_beg,
            dynasty_end_yr=dyn_end,
        )
    except Exception as e:
        raise HTTPException(status_code=422, detail=f'地名匹配失败: {e}') from e

    route_lines = build_routes(campaign.routes, features)
    geojson = make_geojson(features, route_lines)

    return ExtractResponse(
        extract_id=uuid.uuid4().hex[:12],
        campaign_name=campaign.campaign_name,
        factions=[f.model_dump(by_alias=True) for f in campaign.factions],
        features=[f.model_dump() for f in features],
        routes=[r.model_dump() for r in route_lines],
        geojson=geojson,
        scale=campaign.scale,
    )
