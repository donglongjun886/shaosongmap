"""services/unit_banner.py 单元测试：部队旗帜标记、_slot 槽位分配、GeoJSON 生成。"""

from shaosongmap.models import ForceUnit, GeoFeature, UnitState
from shaosongmap.services.unit_banner import (
    _assign_slots,
    make_unit_banner_features,
    make_unit_geojson,
)


class TestMakeUnitBannerFeatures:
    def test_point_feature_created(self):
        result = make_unit_banner_features(
            lng=114.0,
            lat=34.0,
            angle_deg=None,
            direction_name=None,
            direction_len_m=5000.0,
            unit_name='中军',
            faction='宋军',
            status='deploying',
            seq=1,
            description='列阵',
            scale='battle',
        )
        assert len(result) == 1
        feat = result[0]
        assert feat['type'] == 'Feature'
        assert feat['geometry']['type'] == 'Point'
        assert feat['geometry']['coordinates'] == [114.0, 34.0]
        assert feat['properties']['unit_name'] == '中军'
        assert feat['properties']['faction'] == '宋军'
        assert feat['properties']['_feature_type'] == 'unit_banner'

    def test_with_direction_adds_linestring(self):
        result = make_unit_banner_features(
            lng=114.0,
            lat=34.0,
            angle_deg=90.0,
            direction_name='北',
            direction_len_m=5000.0,
            unit_name='左军',
            faction='宋军',
            status='marching',
            seq=2,
            description='北进',
            scale='battle',
        )
        assert len(result) == 2
        line = result[1]
        assert line['geometry']['type'] == 'LineString'
        assert line['properties']['_feature_type'] == 'unit_direction'
        assert len(line['geometry']['coordinates']) == 2

    def test_properties_passed_through(self):
        result = make_unit_banner_features(
            lng=114.0,
            lat=34.0,
            angle_deg=None,
            direction_name=None,
            direction_len_m=5000.0,
            unit_name='右军',
            faction='金军',
            status='retreating',
            seq=3,
            description='撤退',
            scale='strategic',
        )
        props = result[0]['properties']
        assert props['step'] == 3
        assert props['status'] == 'retreating'
        assert props['scale'] == 'strategic'
        assert props['description'] == '撤退'


class TestAssignSlots:
    def test_single_unit_slot_zero(self):
        coord_map = {'汴京': [114.0, 34.0]}
        effective = {
            '中军': UnitState(seq=1, unit_name='中军', status='deploying', location='汴京')
        }
        slots = _assign_slots(effective, coord_map)
        assert slots == {'中军': 0}

    def test_multiple_units_same_location_sorted_by_name(self):
        coord_map = {'汴京': [114.0, 34.0]}
        effective = {
            '右军': UnitState(seq=1, unit_name='右军', status='deploying', location='汴京'),
            '左军': UnitState(seq=1, unit_name='左军', status='deploying', location='汴京'),
            '中军': UnitState(seq=1, unit_name='中军', status='deploying', location='汴京'),
        }
        slots = _assign_slots(effective, coord_map)
        assert len(slots) == 3
        # 三个部队按名称字母序分配唯一 slot（0/1/2 各不同）
        assert set(slots.values()) == {0, 1, 2}

    def test_units_at_different_locations_each_slot_zero(self):
        coord_map = {'汴京': [114.0, 34.0], '襄阳': [112.0, 32.0]}
        effective = {
            '左军': UnitState(seq=1, unit_name='左军', status='deploying', location='汴京'),
            '右军': UnitState(seq=1, unit_name='右军', status='deploying', location='襄阳'),
        }
        slots = _assign_slots(effective, coord_map)
        assert slots == {'左军': 0, '右军': 0}

    def test_missing_location_skipped(self):
        coord_map = {'汴京': [114.0, 34.0]}
        effective = {
            '中军': UnitState(seq=1, unit_name='中军', status='deploying', location=None),
        }
        slots = _assign_slots(effective, coord_map)
        assert slots == {}


class TestMakeUnitGeojson:
    def test_empty_unit_states(self):
        result = make_unit_geojson([], [], [], None)
        assert result == []

    def test_single_unit_single_step(self):
        units = [ForceUnit(name='中军', faction='宋军', direction='东')]
        states = [UnitState(seq=1, unit_name='中军', status='deploying', location='汴京')]
        features = [GeoFeature(name='汴京', lng=114.0, lat=34.0)]
        result = make_unit_geojson(units, states, features, 'battle')
        assert len(result) >= 1
        point = [f for f in result if f['geometry']['type'] == 'Point']
        assert len(point) == 1
        assert point[0]['properties']['unit_name'] == '中军'
        assert point[0]['properties']['_slot'] == 0
        # 坐标保留真实值（无偏移）
        assert point[0]['geometry']['coordinates'] == [114.0, 34.0]

    def test_unit_progresses_through_steps(self):
        units = [ForceUnit(name='中军', faction='宋军')]
        states = [
            UnitState(seq=1, unit_name='中军', status='deploying', location='汴京'),
            UnitState(seq=2, unit_name='中军', status='marching', location='汴京'),
        ]
        features = [GeoFeature(name='汴京', lng=114.0, lat=34.0)]
        result = make_unit_geojson(units, states, features, 'battle')
        # 两个步骤各一份 feature
        points = [f for f in result if f['geometry']['type'] == 'Point']
        assert len(points) == 2
        assert points[0]['properties']['step'] == 1
        assert points[1]['properties']['step'] == 2

    def test_unit_with_unknown_location_skipped(self):
        units = [ForceUnit(name='中军', faction='宋军')]
        states = [UnitState(seq=1, unit_name='中军', status='deploying', location='未知地')]
        features = [GeoFeature(name='汴京', lng=114.0, lat=34.0)]
        result = make_unit_geojson(units, states, features, 'battle')
        assert result == []

    def test_multiple_units_multiple_steps(self):
        units = [
            ForceUnit(name='左军', faction='宋军'),
            ForceUnit(name='右军', faction='宋军'),
        ]
        states = [
            UnitState(seq=1, unit_name='左军', status='deploying', location='汴京'),
            UnitState(seq=1, unit_name='右军', status='deploying', location='汴京'),
            UnitState(seq=2, unit_name='左军', status='marching', location='襄阳'),
        ]
        features = [
            GeoFeature(name='汴京', lng=114.0, lat=34.0),
            GeoFeature(name='襄阳', lng=112.0, lat=32.0),
        ]
        result = make_unit_geojson(units, states, features, 'battle')
        points = [f for f in result if f['geometry']['type'] == 'Point']
        # 右军在 seq2 保留有效状态（seq1），因此每个步骤渲染 2 个部队 = 4 个点
        assert len(points) == 4
        # 验证 seq1 和 seq2 都存在
        steps = {p['properties']['step'] for p in points}
        assert steps == {1, 2}

    def test_unit_state_uses_own_direction_over_unit_default(self):
        units = [ForceUnit(name='中军', faction='宋军', direction='东')]
        states = [
            UnitState(seq=1, unit_name='中军', status='marching', location='汴京', direction='北'),
        ]
        features = [GeoFeature(name='汴京', lng=114.0, lat=34.0)]
        result = make_unit_geojson(units, states, features, 'battle')
        lines = [f for f in result if f['geometry']['type'] == 'LineString']
        assert len(lines) >= 1
        coords = lines[0]['geometry']['coordinates']
        assert coords[1][1] > coords[0][1]  # 终点纬度 > 起点

    def test_slot_assigned_for_multiple_units_same_location(self):
        units = [
            ForceUnit(name='左军', faction='宋军'),
            ForceUnit(name='右军', faction='宋军'),
        ]
        states = [
            UnitState(seq=1, unit_name='左军', status='deploying', location='汴京'),
            UnitState(seq=1, unit_name='右军', status='deploying', location='汴京'),
        ]
        features = [GeoFeature(name='汴京', lng=114.0, lat=34.0)]
        result = make_unit_geojson(units, states, features, 'battle')
        points = [f for f in result if f['geometry']['type'] == 'Point']
        assert len(points) == 2
        # 同坐标部队分配不同 _slot
        slots = {p['properties']['unit_name']: p['properties']['_slot'] for p in points}
        assert slots['左军'] != slots['右军']
        assert set(slots.values()) == {0, 1}
        # 坐标均为真实值（无偏移）
        for p in points:
            assert p['geometry']['coordinates'] == [114.0, 34.0]

    def test_slot_present_on_direction_features(self):
        units = [
            ForceUnit(name='左军', faction='宋军'),
            ForceUnit(name='右军', faction='宋军'),
        ]
        states = [
            UnitState(seq=1, unit_name='左军', status='marching', location='汴京', direction='东'),
            UnitState(seq=1, unit_name='右军', status='marching', location='汴京', direction='北'),
        ]
        features = [GeoFeature(name='汴京', lng=114.0, lat=34.0)]
        result = make_unit_geojson(units, states, features, 'battle')
        lines = [f for f in result if f['geometry']['type'] == 'LineString']
        assert len(lines) == 2
        # 方向线也带有 _slot
        for line in lines:
            assert '_slot' in line['properties']
        # 方向线起点为真实坐标
        for line in lines:
            assert line['geometry']['coordinates'][0] == [114.0, 34.0]
