"""/api/extract 路由：SSE 流式提取管道。

采用 PipelineStage 分层：服务层 generator yield PipelineStage 对象，
路由层负责 SSE 序列化，实现传输格式与业务逻辑解耦。
"""

from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Generator
from dataclasses import dataclass

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from shaosongmap.extractor import extract, extract_timeline
from shaosongmap.geocoder import geocode
from shaosongmap.schemas import ExtractRequest
from shaosongmap.services.geo import _DYNASTY_YEARS
from shaosongmap.services.geojson import build_routes, make_geojson
from shaosongmap.services.unit_banner import make_unit_geojson
from shaosongmap.utils import sse_event

logger = logging.getLogger('shaosongmap')

router = APIRouter()


@dataclass
class PipelineStage:
    """管道阶段数据，解耦服务层与传输层。"""

    event: str
    data: dict


def run_extract_pipeline(
    text: str,
    dynasty: str | None,
    mode: str | None,
) -> Generator[PipelineStage, None, None]:
    """执行提取管道：提取 → 地理编码 → 渲染 → 部队标记。

    同步 generator，yield PipelineStage 对象。
    路由层负责将 PipelineStage 序列化为 SSE 格式，便于独立测试。
    """
    t_pipeline_start = time.perf_counter()
    use_timeline = mode == 'timeline'

    # Stage 1: Extract
    t0 = time.perf_counter()
    try:
        campaign = extract_timeline(text) if use_timeline else extract(text)
    except ValueError as e:
        yield PipelineStage('error', {'stage': 'extract', 'message': str(e)})
        return

    extract_elapsed = (time.perf_counter() - t0) * 1000
    places_count = len(campaign.places)
    routes_count = len(campaign.routes)
    events_count = len(getattr(campaign, 'events', []))
    extract_detail = f'提取结构数据 ({places_count}地名, {routes_count}路线'
    if use_timeline:
        extract_detail += f', {events_count}事件'
    extract_detail += ')'
    logger.info('Stage 1 提取: %s, 耗时 %.0fms', extract_detail, extract_elapsed)
    yield PipelineStage(
        'progress',
        {
            'stage': 'extract_done',
            'detail': extract_detail,
            'ok': True,
            'elapsed_ms': round(extract_elapsed),
        },
    )

    # Stage 2: Geocode
    dyn_beg, dyn_end = None, None
    if dynasty and dynasty in _DYNASTY_YEARS:
        dyn_beg, dyn_end = _DYNASTY_YEARS[dynasty]

    t0 = time.perf_counter()
    try:
        features = geocode(
            campaign.places,
            context_text=text,
            dynasty_beg_yr=dyn_beg,
            dynasty_end_yr=dyn_end,
        )
    except Exception as e:
        yield PipelineStage('error', {'stage': 'geocode', 'message': str(e)})
        return

    geocode_elapsed = (time.perf_counter() - t0) * 1000
    chgis_count = sum(1 for f in features if f.source == 'chgis')
    llm_count = sum(1 for f in features if f.source == 'llm_infer')
    logger.info(
        'Stage 2 地理编码: %d CHGIS + %d LLM, 耗时 %.0fms',
        chgis_count,
        llm_count,
        geocode_elapsed,
    )
    yield PipelineStage(
        'progress',
        {
            'stage': 'geocode_done',
            'detail': f'匹配古地名 ({chgis_count} CHGIS + {llm_count} LLM推断)',
            'ok': True,
            'elapsed_ms': round(geocode_elapsed),
        },
    )

    # Stage 3: Build routes & GeoJSON
    t0 = time.perf_counter()
    route_lines = build_routes(campaign.routes, features)
    timeline_events = getattr(campaign, 'events', []) if use_timeline else None
    geojson = make_geojson(features, route_lines, events=timeline_events)

    render_elapsed = (time.perf_counter() - t0) * 1000
    render_detail = f'渲染地图 ({len(features)}标记, {len(route_lines)}路线)'
    if use_timeline and timeline_events:
        render_detail += f', {len(timeline_events)}步骤'
    logger.info('Stage 3 渲染: %s, 耗时 %.0fms', render_detail, render_elapsed)
    yield PipelineStage(
        'progress',
        {
            'stage': 'render_done',
            'detail': render_detail,
            'ok': True,
            'elapsed_ms': round(render_elapsed),
        },
    )

    # Stage 3.5: Unit GeoJSON (timeline mode only)
    if use_timeline:
        timeline_units = getattr(campaign, 'units', [])
        timeline_unit_states = getattr(campaign, 'unit_states', [])
        if timeline_units and timeline_unit_states:
            unit_features = make_unit_geojson(
                timeline_units,
                timeline_unit_states,
                features,
                campaign.scale,
            )
            geojson['features'].extend(unit_features)

    # Final result
    total_elapsed = (time.perf_counter() - t_pipeline_start) * 1000
    logger.info(
        '管道全部完成: 总耗时 %.0fms (提取 %.0f + 编码 %.0f + 渲染 %.0f)',
        total_elapsed,
        extract_elapsed,
        geocode_elapsed,
        render_elapsed,
    )
    result: dict = {
        'extract_id': uuid.uuid4().hex[:12],
        'campaign_name': campaign.campaign_name,
        'factions': [f.model_dump(by_alias=True) for f in campaign.factions],
        'features': [f.model_dump() for f in features],
        'routes': [r.model_dump() for r in route_lines],
        'geojson': geojson,
        'scale': campaign.scale,
        'elapsed': {
            'extract_ms': round(extract_elapsed),
            'geocode_ms': round(geocode_elapsed),
            'render_ms': round(render_elapsed),
            'total_ms': round(total_elapsed),
        },
    }
    if use_timeline and timeline_events:
        result['events'] = [e.model_dump() for e in timeline_events]
        result['total_steps'] = len(timeline_events)
        if timeline_units:
            result['units'] = [u.model_dump() for u in timeline_units]
        if timeline_unit_states:
            result['unit_states'] = [us.model_dump() for us in timeline_unit_states]
    yield PipelineStage('result', result)


@router.post('/api/extract')
async def extract_campaign(request: ExtractRequest):
    """从战役文本中提取结构化数据并返回地图要素（SSE 流式）。

    通过 Server-Sent Events 推送管道各阶段进度，
    最终以 result 事件返回完整数据。
    """
    if not request.text.strip():
        raise HTTPException(status_code=422, detail='战役文本不能为空')

    async def event_stream():
        for stage in run_extract_pipeline(request.text, request.dynasty, request.mode):
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
