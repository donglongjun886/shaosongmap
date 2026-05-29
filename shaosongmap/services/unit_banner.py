"""部队旗帜渲染服务：汉代《驻军图》风格双线套框标记。"""

from __future__ import annotations

import logging
from collections import defaultdict

from shaosongmap.models import ForceUnit, GeoFeature, UnitState
from shaosongmap.services.geo import angle_for_direction, compute_data_diagonal, offset_point

logger = logging.getLogger(__name__)


def make_unit_banner_features(
    lng: float,
    lat: float,
    angle_deg: float | None,
    direction_name: str | None,
    direction_len_m: float,
    unit_name: str,
    faction: str,
    status: str,
    seq: int,
    description: str,
    scale: str | None,
    direction_target: str | None = None,
) -> list[dict]:
    """为部队生成汉代《驻军图》风格旗帜标记 GeoJSON 特征。

    返回 list，包含：
    - Point 特征：旗帜位置（渲染为双线矩形框图标）
    - LineString 特征（如有方向）：方向指示线
    """

    banner_props = {
        '_feature_type': 'unit_banner',
        'unit_name': unit_name,
        'faction': faction,
        'status': status,
        'step': seq,
        'description': description,
        'direction': direction_name,
        'direction_target': direction_target or None,
        'scale': scale,
    }

    features: list[dict] = [
        {
            'type': 'Feature',
            'geometry': {'type': 'Point', 'coordinates': [lng, lat]},
            'properties': banner_props,
        }
    ]

    if angle_deg is not None:
        end = offset_point(lng, lat, angle_deg, direction_len_m)
        features.append(
            {
                'type': 'Feature',
                'geometry': {'type': 'LineString', 'coordinates': [[lng, lat], end]},
                'properties': {
                    '_feature_type': 'unit_direction',
                    'unit_name': unit_name,
                    'faction': faction,
                    'status': status,
                    'step': seq,
                },
            }
        )

    return features


def make_unit_geojson(
    units: list[ForceUnit],
    unit_states: list[UnitState],
    features: list[GeoFeature],
    scale: str | None,
) -> list[dict]:
    """为部队生成 GeoJSON 特征列表。

    后端仅标记同坐标部队的 _slot 序号，不做像素偏移。
    前端根据实际 zoom 和图标尺寸计算真实偏移量。
    """

    coord_map: dict[str, list[float]] = {}
    for feat in features:
        if feat.lng is not None and feat.lat is not None:
            coord_map[feat.name] = [feat.lng, feat.lat]

    # 方向线长度
    place_coords = [
        (feat.lng, feat.lat) for feat in features if feat.lng is not None and feat.lat is not None
    ]
    diagonal_m = compute_data_diagonal(place_coords)
    scale_ratio = {'tactical': 0.10, 'battle': 0.08, 'strategic': 0.03}
    ratio = scale_ratio.get(scale or '', 0.08)
    direction_len_m = diagonal_m * ratio
    direction_len_m = max(direction_len_m, 500.0)
    direction_len_m = min(direction_len_m, 20000.0)

    unit_map: dict[str, ForceUnit] = {u.name: u for u in units}

    seq_states: dict[int, list[UnitState]] = defaultdict(list)
    all_seqs: set[int] = set()
    for us in unit_states:
        seq_states[us.seq].append(us)
        all_seqs.add(us.seq)

    if not all_seqs:
        return []

    logger.info(
        '生成部队 GeoJSON: %d 部队, %d 状态, %d 步骤',
        len(units),
        len(unit_states),
        len(all_seqs),
    )

    geojson_features: list[dict] = []

    for current_seq in sorted(all_seqs):
        effective: dict[str, UnitState] = {}
        for us in unit_states:
            if us.seq > current_seq:
                continue
            if us.unit_name not in effective or us.seq > effective[us.unit_name].seq:
                effective[us.unit_name] = us

        for unit_name, us in effective.items():
            unit = unit_map.get(unit_name)
            location = us.location
            if not location or location not in coord_map:
                continue

            base = coord_map[location]

            direction = us.direction or (unit.direction if unit else None)
            angle = angle_for_direction(direction) if direction else None

            feat_list = make_unit_banner_features(
                base[0],
                base[1],
                angle,
                direction,
                direction_len_m,
                unit_name,
                unit.faction if unit else '',
                us.status,
                current_seq,
                us.description,
                scale,
                getattr(us, 'direction_target', None),
            )
            geojson_features.extend(feat_list)

    logger.info('部队 GeoJSON 完成: %d 要素', len(geojson_features))
    return geojson_features
