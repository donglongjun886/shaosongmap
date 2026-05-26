"""地理计算服务：方向角/距离/坐标偏移。"""

from __future__ import annotations

import logging
import math

logger = logging.getLogger(__name__)

# 朝代时间范围映射
_DYNASTY_YEARS: dict[str, tuple[int, int]] = {
    '北宋': (960, 1127),
    '南宋': (1127, 1279),
    '宋': (960, 1279),
    '唐': (618, 907),
    '明': (1368, 1644),
    '清': (1644, 1911),
}

# 进攻方位 → 角度（正东=0°，逆时针）
_DIRECTION_ANGLE: dict[str, float] = {
    '东': 0,
    '南': 270,
    '西': 180,
    '北': 90,
    '东南': 315,
    '西南': 225,
    '东北': 45,
    '西北': 135,
}


def angle_for_direction(direction: str | None) -> float:
    """将方位词转换为角度，默认 0°（正东）。"""
    if direction and direction in _DIRECTION_ANGLE:
        return _DIRECTION_ANGLE[direction]
    return 0.0


def compute_data_diagonal(place_coords: list[tuple[float, float]]) -> float:
    """计算数据包围盒对角线长度（米），用于自适应箭头尺寸。"""
    if not place_coords or len(place_coords) < 2:
        return 100.0  # 单点默认100m
    lngs = [c[0] for c in place_coords]
    lats = [c[1] for c in place_coords]
    min_lng, max_lng = min(lngs), max(lngs)
    min_lat, max_lat = min(lats), max(lats)
    mid_lat = math.radians((min_lat + max_lat) / 2)
    dx = (max_lng - min_lng) * 111320.0 * math.cos(mid_lat)
    dy = (max_lat - min_lat) * 111320.0
    return math.sqrt(dx * dx + dy * dy)


def offset_point(
    lng: float,
    lat: float,
    angle_deg: float,
    distance_m: float,
) -> list[float]:
    """从给定点沿给定角度偏移指定距离（米），返回 [lng, lat]."""
    lat_rad = math.radians(lat)
    angle_rad = math.radians(angle_deg)
    d_lng = distance_m * math.cos(angle_rad) / (111320.0 * math.cos(lat_rad))
    d_lat = distance_m * math.sin(angle_rad) / 111320.0
    return [lng + d_lng, lat + d_lat]
