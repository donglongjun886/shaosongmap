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


def compute_unit_offsets(
    unit_states: list[UnitState],
    units: list[ForceUnit],
    features: list[GeoFeature],
    scale: str | None,
) -> dict[str, list[float]]:
    """计算同名地多部队的平行错位偏移。

    同一地点有多个部队时，统一沿南北方向做平行错位展开，
    避免各部队方向角不同导致偏移方向不一致而重叠。

    Returns:
        映射: unit_name → [offset_lng, offset_lat]
    """

    # 建立地名→坐标映射
    coord_map: dict[str, list[float]] = {}
    for feat in features:
        if feat.lng is not None and feat.lat is not None:
            coord_map[feat.name] = [feat.lng, feat.lat]

    # 统计每个坐标点有多少部队（按实际坐标分组，而非地名）
    coord_units: dict[tuple[float, ...], list[str]] = {}
    for us in unit_states:
        if us.location and us.location in coord_map:
            coord = tuple(coord_map[us.location])
            if coord not in coord_units:
                coord_units[coord] = []
            if us.unit_name not in coord_units[coord]:
                coord_units[coord].append(us.unit_name)

    # 同坐标多部队错位展开：按预期 zoom 级别计算像素间距 → 换算为米 → 经纬度偏移
    import math as _m

    lats = [c[1] for c in coord_map.values() if c[1] is not None]
    mid_lat = _m.radians(sum(lats) / len(lats)) if lats else _m.radians(35)

    # 各尺度下期望的图标像素间距（确保肉眼可分辨）
    _ZOOM_PX = {'tactical': (14, 65), 'battle': (10, 50), 'strategic': (6, 40)}
    zoom, target_px = _ZOOM_PX.get(scale or '', (10, 50))
    m_per_px = 156543.0 * _m.cos(mid_lat) / (2**zoom)
    spacing_m = target_px * m_per_px  # 理想像素间距换算为实际米数

    deg_per_m_lat = 1.0 / 111320.0
    offsets: dict[str, list[float]] = {}
    for _coord, unit_names in coord_units.items():
        if len(unit_names) <= 1:
            continue
        for i, uname in enumerate(unit_names):
            # 沿南北方向错位，以中心为基准向两侧分布
            offset_idx = i - (len(unit_names) - 1) / 2
            offset_m = offset_idx * spacing_m
            offsets[uname] = [0.0, offset_m * deg_per_m_lat]

    return offsets


def make_unit_geojson(
    units: list[ForceUnit],
    unit_states: list[UnitState],
    features: list[GeoFeature],
    scale: str | None,
) -> list[dict]:
    """为部队生成汉代《驻军图》风格旗帜标记 GeoJSON 特征列表。

    每个步骤只渲染每个部队的「最新状态」（seq <= 当前步骤的最新 unit_state），
    避免同一部队在多个历史位置同时显示。
    """

    # 建立地名→坐标映射
    coord_map: dict[str, list[float]] = {}
    for feat in features:
        if feat.lng is not None and feat.lat is not None:
            coord_map[feat.name] = [feat.lng, feat.lat]

    # 计算同地多部队偏移（基于所有状态一次算出，偏移量不随步骤变化）
    offsets = compute_unit_offsets(unit_states, units, features, scale)

    # 计算数据范围对角线，用于自适应方向线长度
    place_coords = [
        (feat.lng, feat.lat) for feat in features if feat.lng is not None and feat.lat is not None
    ]
    diagonal_m = compute_data_diagonal(place_coords)
    scale_ratio = {'tactical': 0.10, 'battle': 0.08, 'strategic': 0.03}
    ratio = scale_ratio.get(scale or '', 0.08)
    direction_len_m = diagonal_m * ratio
    direction_len_m = max(direction_len_m, 500.0)  # 最小500m
    direction_len_m = min(direction_len_m, 20000.0)  # 最大20km

    # 建立部队名→部队对象映射
    unit_map: dict[str, ForceUnit] = {u.name: u for u in units}

    # 按 seq 分组 unit_states，同时记录所有步骤号
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

    # 对每个步骤，计算每个部队的「有效状态」（最新且 ≤ 当前步骤）
    for current_seq in sorted(all_seqs):
        # 为每个部队找到最新的 unit_state (seq <= current_seq)
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
            offset = offsets.get(unit_name, [0, 0])
            anchor_lng = base[0] + offset[0]
            anchor_lat = base[1] + offset[1]

            # 方向：优先 unit_state，回退到 unit 级别默认方向
            direction = us.direction or (unit.direction if unit else None)
            angle = angle_for_direction(direction) if direction else None

            feat_list = make_unit_banner_features(
                anchor_lng,
                anchor_lat,
                angle,
                direction,
                direction_len_m,
                unit_name,
                unit.faction if unit else '',
                us.status,
                current_seq,
                us.description,
                scale,
            )
            geojson_features.extend(feat_list)

    logger.info('部队 GeoJSON 完成: %d 要素', len(geojson_features))
    return geojson_features
