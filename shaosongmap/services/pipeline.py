"""提取管道编排服务：提取 → 地理编码 → GeoJSON（仅地名，不产路线）。

同步函数，路由层直接调用获取结果。
"""

from __future__ import annotations

import logging
import time
import uuid

from shaosongmap.extractor import extract
from shaosongmap.geocoder import geocode
from shaosongmap.services.geo import DYNASTY_YEARS
from shaosongmap.services.geojson import make_geojson

logger = logging.getLogger(__name__)


def run_extract_pipeline(
    text: str,
    dynasty: str | None,
) -> dict:
    """执行提取管道：提取 → 地理编码 → GeoJSON。

    一次调用完成全部流程，返回完整结果字典。
    仅提取地名（Point），不再产出行军路线（LineString）。

    Args:
        text: 战役文本内容
        dynasty: 朝代提示（如「宋」「北宋」「南宋」），用于 CHGIS 时间过滤

    Returns:
        包含 extract_id、event_name、boundaries、person_places、features、geojson、scale、elapsed 的字典

    Raises:
        ValueError: 提取阶段失败
    """
    t_start = time.perf_counter()

    # Stage 1: Extract
    t0 = time.perf_counter()
    campaign = extract(text)
    extract_elapsed = (time.perf_counter() - t0) * 1000
    logger.info(
        'Stage 1 提取: %d地名, %d人物地点关联, %d边界, 耗时 %.0fms',
        len(campaign.places),
        len(campaign.person_places),
        len(campaign.boundaries),
        extract_elapsed,
    )

    # Stage 2: Geocode
    dyn_beg, dyn_end = None, None
    if dynasty and dynasty in DYNASTY_YEARS:
        dyn_beg, dyn_end = DYNASTY_YEARS[dynasty]

    try:
        t0 = time.perf_counter()
        features = geocode(
            campaign.places,
            context_text=text,
            dynasty_beg_yr=dyn_beg,
            dynasty_end_yr=dyn_end,
        )
        geocode_elapsed = (time.perf_counter() - t0) * 1000
        logger.info(
            'Stage 2 地理编码: %d CHGIS + %d LLM, 耗时 %.0fms',
            sum(1 for f in features if f.source == 'chgis'),
            sum(1 for f in features if f.source == 'llm_infer'),
            geocode_elapsed,
        )
    except Exception as e:
        logger.error('Stage 2 地理编码异常: %s', e)
        raise ValueError(f'地理编码失败: {e}') from e

    # Stage 3: Build GeoJSON (Point only, no LineString)
    try:
        t0 = time.perf_counter()
        geojson = make_geojson(features)
        render_elapsed = (time.perf_counter() - t0) * 1000
        logger.info('Stage 3 渲染: %d 标记, 耗时 %.0fms', len(features), render_elapsed)
    except Exception as e:
        logger.error('Stage 3 渲染异常: %s', e)
        raise ValueError(f'GeoJSON 构建失败: {e}') from e

    total_elapsed = (time.perf_counter() - t_start) * 1000
    logger.info('管道全部完成: 总耗时 %.0fms', total_elapsed)

    return {
        'extract_id': uuid.uuid4().hex[:12],
        'event_name': campaign.event_name,
        'dynasty': campaign.dynasty,
        'boundaries': [b.model_dump() for b in campaign.boundaries],
        'person_places': [pp.model_dump() for pp in campaign.person_places],
        'places': [p.model_dump() for p in campaign.places],
        'features': [f.model_dump() for f in features],
        'geojson': geojson,
        'scale': campaign.scale,
        'elapsed': {
            'extract_ms': round(extract_elapsed),
            'geocode_ms': round(geocode_elapsed),
            'render_ms': round(render_elapsed),
            'total_ms': round(total_elapsed),
        },
    }
