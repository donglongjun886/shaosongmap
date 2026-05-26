"""services/geo.py 单元测试：角度转换、距离计算、坐标偏移。"""

import pytest

from shaosongmap.services.geo import angle_for_direction, compute_data_diagonal, offset_point


class TestAngleForDirection:
    def test_east_returns_0(self):
        assert angle_for_direction('东') == 0.0

    def test_west_returns_180(self):
        assert angle_for_direction('西') == 180.0

    def test_south_returns_270(self):
        assert angle_for_direction('南') == 270.0

    def test_north_returns_90(self):
        assert angle_for_direction('北') == 90.0

    def test_northeast_returns_45(self):
        assert angle_for_direction('东北') == 45.0

    def test_southwest_returns_225(self):
        assert angle_for_direction('西南') == 225.0

    def test_none_returns_0(self):
        assert angle_for_direction(None) == 0.0

    def test_empty_string_returns_0(self):
        assert angle_for_direction('') == 0.0

    def test_unknown_direction_returns_0(self):
        assert angle_for_direction('天') == 0.0


class TestComputeDataDiagonal:
    def test_two_points(self):
        coords = [(116.0, 39.0), (117.0, 40.0)]
        result = compute_data_diagonal(coords)
        assert result > 0
        assert result < 200000  # 合理范围

    def test_many_points(self):
        coords = [(116.0, 39.0), (117.0, 40.0), (115.5, 38.5)]
        result = compute_data_diagonal(coords)
        assert result > 50000

    def test_empty_list_returns_default(self):
        assert compute_data_diagonal([]) == 100.0

    def test_single_point_returns_default(self):
        assert compute_data_diagonal([(116.0, 39.0)]) == 100.0

    def test_identical_points(self):
        coords = [(116.0, 39.0), (116.0, 39.0)]
        result = compute_data_diagonal(coords)
        assert result == 0.0


class TestOffsetPoint:
    def test_offset_east(self):
        result = offset_point(116.0, 39.0, 0.0, 1000.0)
        assert result[0] > 116.0  # 经度增加
        assert result[1] == pytest.approx(39.0, abs=0.001)  # 纬度不变

    def test_offset_north(self):
        result = offset_point(116.0, 39.0, 90.0, 1000.0)
        assert result[0] == pytest.approx(116.0, abs=0.001)
        assert result[1] > 39.0  # 纬度增加

    def test_offset_west(self):
        result = offset_point(116.0, 39.0, 180.0, 1000.0)
        assert result[0] < 116.0
        assert result[1] == pytest.approx(39.0, abs=0.001)

    def test_offset_south(self):
        result = offset_point(116.0, 39.0, 270.0, 1000.0)
        assert result[0] == pytest.approx(116.0, abs=0.001)
        assert result[1] < 39.0

    def test_offset_northeast(self):
        result = offset_point(116.0, 39.0, 45.0, 1000.0)
        assert result[0] > 116.0
        assert result[1] > 39.0

    def test_zero_distance(self):
        result = offset_point(116.0, 39.0, 45.0, 0.0)
        assert result[0] == 116.0
        assert result[1] == 39.0

    def test_return_type_is_list(self):
        result = offset_point(116.0, 39.0, 90.0, 500.0)
        assert isinstance(result, list)
        assert len(result) == 2

    def test_distance_symmetry(self):
        """正方向走一段 + 反方向走回原点近似一致。"""
        original = [116.0, 39.0]
        forward = offset_point(original[0], original[1], 60.0, 500.0)
        back = offset_point(forward[0], forward[1], 240.0, 500.0)
        assert back[0] == pytest.approx(original[0], abs=0.0001)
        assert back[1] == pytest.approx(original[1], abs=0.0001)
