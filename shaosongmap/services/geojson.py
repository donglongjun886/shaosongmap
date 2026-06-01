"""GeoJSON 构建服务：地名坐标 → GeoJSON FeatureCollection（仅 Point 类型）。"""

from __future__ import annotations

import logging

from shaosongmap.models import GeoFeature

logger = logging.getLogger(__name__)


def make_geojson(features: list[GeoFeature]) -> dict:
    """将 GeoFeature 列表转换为 GeoJSON FeatureCollection（仅 Point 要素）。

    Args:
        features: 地名坐标特征列表

    Returns:
        GeoJSON FeatureCollection 字典，仅包含 Point 类型的 Feature
    """
    geojson_features = []

    for feat in features:
        if feat.lng is not None and feat.lat is not None:
            geojson_features.append(
                {
                    'type': 'Feature',
                    'geometry': {'type': 'Point', 'coordinates': [feat.lng, feat.lat]},
                    'properties': {
                        'name': feat.name,
                        'source': feat.source,
                        'modern_name': feat.modern_name,
                        'confidence': feat.confidence,
                        'place_type': feat.place_type,
                    },
                }
            )

    logger.info('生成 GeoJSON: %d 标记', len(geojson_features))
    return {'type': 'FeatureCollection', 'features': geojson_features}
