"""GeoJSON 构建服务：地图要素和行军路线 → GeoJSON FeatureCollection。"""

from __future__ import annotations

from shaosongmap.models import GeoFeature, RouteLine, TimelineEvent


def compute_step_map(events: list[TimelineEvent]) -> dict[str, int]:
    """从事件序列计算每个地名首次被激活的步骤编号。"""
    step_map: dict[str, int] = {}
    for event in events:
        for place_name in event.places_involved:
            if place_name not in step_map:
                step_map[place_name] = event.seq
    return step_map


def build_routes(
    places,
    features: list[GeoFeature],
) -> list[RouteLine]:
    """根据提取的行军路线和地标坐标构建 GeoJSON 路线线段。

    将相邻路标坐标两两连接，形成行军路线折线。
    """
    from shaosongmap.models import RouteLine as RL

    # 建立地名 → 坐标映射
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
                RL(
                    from_place=route.from_place,
                    to_place=route.to_place,
                    coordinates=coords,
                )
            )

    return route_lines


def make_geojson(
    features: list[GeoFeature],
    routes: list[RouteLine],
    events: list[TimelineEvent] | None = None,
) -> dict:
    """将 GeoFeature 和 RouteLine 列表转换为 GeoJSON FeatureCollection。

    timeline 模式下（提供 events 参数），每个 feature 的 properties
    中注入 step 属性，供前端按步骤过滤渲染。
    """
    step_map: dict[str, int] | None = None
    if events:
        step_map = compute_step_map(events)

    geojson_features = []

    for feat in features:
        if feat.lng is not None and feat.lat is not None:
            props: dict = {
                'name': feat.name,
                'source': feat.source,
                'modern_name': feat.modern_name,
                'confidence': feat.confidence,
                'place_type': feat.place_type,
            }
            if step_map is not None:
                props['step'] = step_map.get(feat.name, 0)
            geojson_features.append(
                {
                    'type': 'Feature',
                    'geometry': {
                        'type': 'Point',
                        'coordinates': [feat.lng, feat.lat],
                    },
                    'properties': props,
                }
            )

    for route in routes:
        if len(route.coordinates) >= 2:
            route_props: dict = {
                'type': 'route',
                'from': route.from_place,
                'to': route.to_place,
            }
            if step_map is not None:
                to_step = step_map.get(route.to_place)
                from_step = step_map.get(route.from_place)
                if to_step is not None:
                    route_props['step'] = to_step
                elif from_step is not None:
                    route_props['step'] = from_step
                else:
                    route_props['step'] = 1
            geojson_features.append(
                {
                    'type': 'Feature',
                    'geometry': {
                        'type': 'LineString',
                        'coordinates': route.coordinates,
                    },
                    'properties': route_props,
                }
            )

    return {
        'type': 'FeatureCollection',
        'features': geojson_features,
    }
