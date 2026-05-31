"""GeoJSON 构建服务：地图要素和行军路线 → GeoJSON FeatureCollection。"""

from __future__ import annotations

import logging

from shaosongmap.models import GeoFeature, RouteLine

logger = logging.getLogger(__name__)


def build_routes(
    places,
    features: list[GeoFeature],
) -> list[RouteLine]:
    """根据提取的行军路线和地标坐标构建 GeoJSON 路线线段。"""
    from shaosongmap.models import RouteLine as RL

    coord_map: dict[str, list[float]] = {}
    for feat in features:
        if feat.lng is not None and feat.lat is not None:
            coord_map[feat.name] = [feat.lng, feat.lat]

    route_lines: list[RouteLine] = []
    for route in places:
        coords = []
        start_coord = coord_map.get(route.from_place)
        if start_coord:
            coords.append(start_coord)

        for via_place in route.via:
            via_coord = coord_map.get(via_place)
            if via_coord:
                coords.append(via_coord)

        end_coord = coord_map.get(route.to_place)
        if end_coord:
            coords.append(end_coord)

        if len(coords) >= 2:
            route_lines.append(
                RL(from_place=route.from_place, to_place=route.to_place, coordinates=coords)
            )

    logger.info('构建路线: %d 输入 → %d 有效线段', len(places), len(route_lines))
    return route_lines


def make_geojson(
    features: list[GeoFeature],
    routes: list[RouteLine],
) -> dict:
    """将 GeoFeature 和 RouteLine 列表转换为 GeoJSON FeatureCollection。"""
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

    for route in routes:
        if len(route.coordinates) >= 2:
            geojson_features.append(
                {
                    'type': 'Feature',
                    'geometry': {'type': 'LineString', 'coordinates': route.coordinates},
                    'properties': {'type': 'route', 'from': route.from_place, 'to': route.to_place},
                }
            )

    logger.info('生成 GeoJSON: %d 标记, %d 路线', len(geojson_features), len(routes))
    return {'type': 'FeatureCollection', 'features': geojson_features}
