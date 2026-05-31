"""提取管道编排服务：提取 → 地理编码 → 渲染。

SSE 传输格式无关的纯业务逻辑，通过 generator yield PipelineStage 对象与路由层解耦。
"""

from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Generator
from dataclasses import dataclass

from shaosongmap.extractor import extract
from shaosongmap.geocoder import geocode
from shaosongmap.services.geo import _DYNASTY_YEARS
from shaosongmap.services.geojson import build_routes, make_geojson

logger = logging.getLogger(__name__)


@dataclass
class PipelineStage:
    """管道阶段数据，解耦服务层与传输层。"""

    event: str
    data: dict


def run_extract_pipeline(
    text: str,
    dynasty: str | None,
) -> Generator[PipelineStage, None, None]:
    """执行提取管道：提取 → 地理编码 → 渲染。

    同步 generator，yield PipelineStage 对象。
    路由层负责将 PipelineStage 序列化为 SSE 格式。
    """
    t_pipeline_start = time.perf_counter()

    # Stage 1: Extract
    t0 = time.perf_counter()
    try:
        campaign = extract(text)
    except ValueError as e:
        yield PipelineStage('error', {'stage': 'extract', 'message': str(e)})
        return

    extract_elapsed = (time.perf_counter() - t0) * 1000
    logger.info(
        'Stage 1 提取: %d地名, %d路线, 耗时 %.0fms',
        len(campaign.places),
        len(campaign.routes),
        extract_elapsed,
    )
    yield PipelineStage(
        'progress',
        {
            'stage': 'extract_done',
            'detail': f'提取结构数据 ({len(campaign.places)}地名, {len(campaign.routes)}路线)',
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
    logger.info(
        'Stage 2 地理编码: %d CHGIS + %d LLM, 耗时 %.0fms',
        sum(1 for f in features if f.source == 'chgis'),
        sum(1 for f in features if f.source == 'llm_infer'),
        geocode_elapsed,
    )
    yield PipelineStage(
        'progress',
        {
            'stage': 'geocode_done',
            'detail': '匹配古地名',
            'ok': True,
            'elapsed_ms': round(geocode_elapsed),
        },
    )

    # Stage 3: Build routes & GeoJSON
    t0 = time.perf_counter()
    route_lines = build_routes(campaign.routes, features)
    geojson = make_geojson(features, route_lines)

    render_elapsed = (time.perf_counter() - t0) * 1000
    logger.info(
        'Stage 3 渲染: %d标记, %d路线, 耗时 %.0fms',
        len(features),
        len(route_lines),
        render_elapsed,
    )
    yield PipelineStage(
        'progress',
        {
            'stage': 'render_done',
            'detail': f'渲染地图 ({len(features)}标记, {len(route_lines)}路线)',
            'ok': True,
            'elapsed_ms': round(render_elapsed),
        },
    )

    # Final result
    total_elapsed = (time.perf_counter() - t_pipeline_start) * 1000
    logger.info(
        '管道全部完成: 总耗时 %.0fms',
        total_elapsed,
    )
    result: dict = {
        'extract_id': uuid.uuid4().hex[:12],
        'campaign_name': campaign.campaign_name,
        'factions': [f.model_dump(by_alias=True) for f in campaign.factions],
        'features': [f.model_dump() for f in features],
        'routes': [r.model_dump() for r in route_lines],
        'geojson': geojson,
        'elapsed': {
            'extract_ms': round(extract_elapsed),
            'geocode_ms': round(geocode_elapsed),
            'render_ms': round(render_elapsed),
            'total_ms': round(total_elapsed),
        },
    }
    yield PipelineStage('result', result)
