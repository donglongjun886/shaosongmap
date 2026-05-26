"""services/unit_banner.py 单元测试：部队旗帜标记、偏移计算、GeoJSON 生成。"""

from shaosongmap.models import ForceUnit, GeoFeature, UnitState
from shaosongmap.services.unit_banner import (
    compute_unit_offsets,
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


class TestComputeUnitOffsets:
    def test_single_unit_no_offset(self):
        unit_states = [UnitState(seq=1, unit_name='中军', status='deploying', location='汴京')]
        units = [ForceUnit(name='中军', faction='宋军')]
        features = [GeoFeature(name='汴京', lng=114.0, lat=34.0)]
        offsets = compute_unit_offsets(unit_states, units, features, 'battle')
        assert offsets == {}  # 单部队无需偏移

    def test_multiple_units_same_location_get_offsets(self):
        unit_states = [
            UnitState(seq=1, unit_name='左军', status='deploying', location='汴京'),
            UnitState(seq=1, unit_name='中军', status='deploying', location='汴京'),
            UnitState(seq=1, unit_name='右军', status='deploying', location='汴京'),
        ]
        units = [
            ForceUnit(name='左军', faction='宋军'),
            ForceUnit(name='中军', faction='宋军'),
            ForceUnit(name='右军', faction='宋军'),
        ]
        features = [GeoFeature(name='汴京', lng=114.0, lat=34.0)]
        offsets = compute_unit_offsets(unit_states, units, features, 'battle')
        assert len(offsets) == 3
        # 偏移是南北方向，经度偏移为 0；中间部队 lat 偏移为 0
        for _uname, offset in offsets.items():
            assert offset[0] == 0.0  # lng offset is 0 (north-south only)
        # 非居中的部队有非零 lat 偏移
        lat_offsets = [abs(o[1]) for o in offsets.values() if abs(o[1]) > 0]
        assert len(lat_offsets) >= 2

    def test_units_at_different_locations_no_offsets(self):
        unit_states = [
            UnitState(seq=1, unit_name='左军', status='deploying', location='汴京'),
            UnitState(seq=1, unit_name='右军', status='deploying', location='襄阳'),
        ]
        units = [
            ForceUnit(name='左军', faction='宋军'),
            ForceUnit(name='右军', faction='宋军'),
        ]
        features = [
            GeoFeature(name='汴京', lng=114.0, lat=34.0),
            GeoFeature(name='襄阳', lng=112.0, lat=32.0),
        ]
        offsets = compute_unit_offsets(unit_states, units, features, 'battle')
        assert offsets == {}

    def test_missing_location_ignored(self):
        unit_states = [
            UnitState(seq=1, unit_name='中军', status='deploying', location=None),
        ]
        units = [ForceUnit(name='中军', faction='宋军')]
        features = [GeoFeature(name='汴京', lng=114.0, lat=34.0)]
        offsets = compute_unit_offsets(unit_states, units, features, 'battle')
        assert offsets == {}

    def test_scale_affects_spacing(self):
        unit_states = [
            UnitState(seq=1, unit_name='左军', status='deploying', location='汴京'),
            UnitState(seq=1, unit_name='右军', status='deploying', location='汴京'),
        ]
        units = [
            ForceUnit(name='左军', faction='宋军'),
            ForceUnit(name='右军', faction='宋军'),
        ]
        # 多个地名形成足够大的包围盒，避免触发 22m 最小间距
        features = [
            GeoFeature(name='汴京', lng=114.0, lat=34.0),
            GeoFeature(name='襄阳', lng=112.0, lat=32.0),
            GeoFeature(name='西安', lng=108.0, lat=34.0),
        ]
        offsets_tactical = compute_unit_offsets(unit_states, units, features, 'tactical')
        offsets_strategic = compute_unit_offsets(unit_states, units, features, 'strategic')
        tactical_offset = abs(list(offsets_tactical.values())[0][1])
        strategic_offset = abs(list(offsets_strategic.values())[0][1])
        assert tactical_offset > strategic_offset


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
        # 方向线应朝北（纬度增加）
        coords = lines[0]['geometry']['coordinates']
        assert coords[1][1] > coords[0][1]  # 终点纬度 > 起点
