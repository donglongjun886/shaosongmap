"""部队实体提取和块状箭头生成功能的单元测试。"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from shaosongmap.extractor import (
    _deduplicate_unit_names,
    _edit_distance,
    _validate_unit_states,
    extract_timeline,
)
from shaosongmap.models import CampaignTimeline, ForceUnit, TroopType, UnitState, UnitStatus

# ── 6.1: 模型校验 ──


def test_force_unit_model():
    """ForceUnit 模型基础字段校验。"""
    unit = ForceUnit(
        name='焦文通部',
        faction='宋军',
        commander='焦文通',
        troop_type='infantry',
        troop_count='数千',
        direction='东南',
    )
    assert unit.name == '焦文通部'
    assert unit.faction == '宋军'
    assert unit.troop_type == 'infantry'
    assert unit.direction == '东南'


def test_force_unit_defaults():
    """ForceUnit 模型默认值。"""
    unit = ForceUnit(name='测试部', faction='宋军')
    assert unit.commander == ''
    assert unit.troop_type == 'mixed'
    assert unit.troop_count == ''
    assert unit.direction is None


def test_unit_state_model():
    """UnitState 模型基础字段校验。"""
    us = UnitState(
        seq=3,
        unit_name='焦文通部',
        status='engaging',
        location='东坡塬',
        direction='东南',
        description='焦文通部转向娄室中军，侧翼包抄',
    )
    assert us.seq == 3
    assert us.status == 'engaging'
    assert us.location == '东坡塬'


def test_unit_state_invalid_status():
    """UnitState 非法 status 抛出 ValidationError。"""
    with pytest.raises(ValueError):
        UnitState(seq=1, unit_name='测试', status='invalid_status')


def test_campaign_timeline_with_units():
    """CampaignTimeline 可携带 units 和 unit_states。"""
    ct = CampaignTimeline.model_validate(
        {
            'campaign_name': '测试战役',
            'factions': [{'name': '宋军', 'commanders': [], 'troops': None}],
            'places': [{'name': '东坡塬', 'context': '塬上'}],
            'routes': [],
            'events': [
                {
                    'seq': 1,
                    'event_type': 'battle',
                    'description': '交战',
                    'actors': [],
                    'places_involved': ['东坡塬'],
                }
            ],
            'units': [
                {
                    'name': '焦文通部',
                    'faction': '宋军',
                    'commander': '焦文通',
                    'troop_type': 'mixed',
                    'troop_count': '数千',
                }
            ],
            'unit_states': [
                {
                    'seq': 1,
                    'unit_name': '焦文通部',
                    'status': 'engaging',
                    'location': '东坡塬',
                    'description': '侧翼包抄',
                }
            ],
        }
    )
    assert len(ct.units) == 1
    assert ct.units[0].name == '焦文通部'
    assert len(ct.unit_states) == 1
    assert ct.unit_states[0].status == 'engaging'


# ── 6.2: 后处理函数 ──


def test_edit_distance_identical():
    """编辑距离：相同字符串距离为 0。"""
    assert _edit_distance('焦文通部', '焦文通部') == 0


def test_edit_distance_one_diff():
    """编辑距离：一个字符差异距离为 1。"""
    assert _edit_distance('焦文通部', '焦文通所部') == 1


def test_edit_distance_totally_different():
    """编辑距离：完全不同。"""
    assert _edit_distance('焦文通部', '郦琼部') > 2


def test_edit_distance_empty():
    """编辑距离：空字符串。"""
    assert _edit_distance('', '焦文通部') == 4
    assert _edit_distance('', '') == 0


def test_deduplicate_unit_names_no_dup():
    """无重复部队名时原样返回。"""
    units = [
        {'name': '焦文通部', 'faction': '宋军'},
        {'name': '郦琼部', 'faction': '宋军'},
    ]
    result = _deduplicate_unit_names(units)
    assert len(result) == 2


def test_deduplicate_unit_names_with_variant():
    """名称变体被合并。"""
    units = [
        {'name': '焦文通部', 'faction': '宋军'},
        {'name': '焦文通所部', 'faction': '宋军'},  # 编辑距离 1，应被合并
    ]
    result = _deduplicate_unit_names(units)
    assert len(result) == 1
    assert result[0]['name'] == '焦文通部'


def test_deduplicate_unit_names_too_short():
    """过短名称不合并（编辑距离判定需要 >= 3 字符）。"""
    units = [
        {'name': '宋', 'faction': '宋军'},
        {'name': '金', 'faction': '金军'},
    ]
    result = _deduplicate_unit_names(units)
    assert len(result) == 2


def test_validate_unit_states_normal():
    """正常 unit_states 全部通过。"""
    units = [{'name': '焦文通部'}]
    events = [{'seq': 1}, {'seq': 2}]
    unit_states = [
        {'seq': 1, 'unit_name': '焦文通部', 'status': 'marching'},
        {'seq': 2, 'unit_name': '焦文通部', 'status': 'engaging'},
    ]
    result = _validate_unit_states(unit_states, units, events)
    assert len(result) == 2


def test_validate_unit_states_invalid_seq():
    """seq 不在 events 中的记录被丢弃。"""
    units = [{'name': '焦文通部'}]
    events = [{'seq': 1}]
    unit_states = [
        {'seq': 1, 'unit_name': '焦文通部', 'status': 'marching'},
        {'seq': 99, 'unit_name': '焦文通部', 'status': 'engaging'},
    ]
    result = _validate_unit_states(unit_states, units, events)
    assert len(result) == 1


def test_validate_unit_states_invalid_unit_name():
    """unit_name 不在 units 中的记录被丢弃。"""
    units = [{'name': '焦文通部'}]
    events = [{'seq': 1}]
    unit_states = [
        {'seq': 1, 'unit_name': '焦文通部', 'status': 'marching'},
        {'seq': 1, 'unit_name': '不存在的部队', 'status': 'engaging'},
    ]
    result = _validate_unit_states(unit_states, units, events)
    assert len(result) == 1


# ── 6.3: 旗帜标记特征生成 ──


class TestUnitBannerFeatures:
    """测试 _make_unit_banner_features 函数。"""

    def test_generates_point_and_linestring(self):
        """每个有方向的部队状态生成 Point + LineString 两个特征。"""
        from shaosongmap.services.unit_banner import make_unit_banner_features

        features = make_unit_banner_features(
            114.0,
            35.0,
            45.0,
            '东北',
            2000,
            '焦文通部',
            '宋',
            'marching',
            2,
            '侧翼包抄',
            'tactical',
        )
        assert len(features) == 2
        assert features[0]['geometry']['type'] == 'Point'
        assert features[0]['properties']['_feature_type'] == 'unit_banner'
        assert features[1]['geometry']['type'] == 'LineString'
        assert features[1]['properties']['_feature_type'] == 'unit_direction'

    def test_no_direction_generates_point_only(self):
        """无方向时仅生成 Point 特征。"""
        from shaosongmap.services.unit_banner import make_unit_banner_features

        features = make_unit_banner_features(
            114.0,
            35.0,
            None,
            None,
            2000,
            '守城军',
            '金',
            'deploying',
            1,
            '据守',
            'battle',
        )
        assert len(features) == 1
        assert features[0]['geometry']['type'] == 'Point'

    def test_point_at_anchor(self):
        """Point 位于锚点坐标。"""
        from shaosongmap.services.unit_banner import make_unit_banner_features

        features = make_unit_banner_features(
            114.0,
            35.0,
            0.0,
            '东',
            2000,
            '测试部',
            '金',
            'deploying',
            1,
            '',
            'battle',
        )
        assert features[0]['geometry']['coordinates'] == [114.0, 35.0]

    def test_direction_line_east(self):
        """向东的方向线经度增大。"""
        from shaosongmap.services.unit_banner import make_unit_banner_features

        features = make_unit_banner_features(
            114.0,
            35.0,
            0.0,
            '东',
            2000,
            '测试部',
            '宋',
            'marching',
            1,
            '',
            'battle',
        )
        line = features[1]['geometry']['coordinates']
        assert line[1][0] > line[0][0]  # 经度增大

    def test_direction_line_north(self):
        """向北的方向线纬度增大。"""
        from shaosongmap.services.unit_banner import make_unit_banner_features

        features = make_unit_banner_features(
            114.0,
            35.0,
            90.0,
            '北',
            2000,
            '测试部',
            '宋',
            'marching',
            1,
            '',
            'battle',
        )
        line = features[1]['geometry']['coordinates']
        assert line[1][1] > line[0][1]  # 纬度增大

    def test_properties_preserved(self):
        """旗帜属性完整传递。"""
        from shaosongmap.services.unit_banner import make_unit_banner_features

        features = make_unit_banner_features(
            114.0,
            35.0,
            0.0,
            '东',
            2000,
            '合扎猛安',
            '金',
            'engaging',
            3,
            '铁骑冲击',
            'tactical',
        )
        props = features[0]['properties']
        assert props['unit_name'] == '合扎猛安'
        assert props['faction'] == '金'
        assert props['status'] == 'engaging'
        assert props['step'] == 3
        assert props['direction'] == '东'


def testangle_for_direction():
    """方位词→角度转换。"""
    from shaosongmap.services.geo import angle_for_direction

    assert angle_for_direction('东') == 0.0
    assert angle_for_direction('北') == 90.0
    assert angle_for_direction('南') == 270.0
    assert angle_for_direction('西北') == 135.0
    assert angle_for_direction('东南') == 315.0
    assert angle_for_direction(None) == 0.0
    assert angle_for_direction('未知') == 0.0


# ── 6.4: 集成测试 ──


def _mock_response(json_data: dict) -> MagicMock:
    choice = MagicMock()
    choice.message.content = json.dumps(json_data)
    resp = MagicMock()
    resp.choices = [choice]
    return resp


TIMELINE_WITH_UNITS = (
    '岳飞率三万兵马自襄阳出发。'
    '焦文通部数千人从侧翼压上，意图夹击金军。'
    '金军合扎猛安一千铁骑从塬底冲击焦文通部，焦文通部全军崩溃。'
)


@patch('shaosongmap.extractor.OpenAI')
def test_extract_timeline_with_units(mock_openai: MagicMock):
    """timeline 模式提取部队实体和状态。"""
    mock_openai.return_value.chat.completions.create.return_value = _mock_response(
        {
            'campaign_name': '测试战役',
            'factions': [
                {'name': '宋军', 'commanders': ['岳飞', '焦文通'], 'troops': '三万'},
                {'name': '金军', 'commanders': [], 'troops': '一千骑'},
            ],
            'places': [
                {'name': '襄阳', 'context': '自襄阳出发'},
                {'name': '东坡塬', 'context': '从塬底'},
            ],
            'routes': [],
            'events': [
                {
                    'seq': 1,
                    'event_type': 'march',
                    'description': '出发',
                    'actors': ['岳飞'],
                    'places_involved': ['襄阳'],
                },
                {
                    'seq': 2,
                    'event_type': 'battle',
                    'description': '焦文通部侧翼包抄',
                    'actors': ['焦文通'],
                    'places_involved': ['东坡塬'],
                },
                {
                    'seq': 3,
                    'event_type': 'battle',
                    'description': '合扎猛安冲击，焦文通部溃散',
                    'actors': ['焦文通', '合扎猛安'],
                    'places_involved': ['东坡塬'],
                },
            ],
            'units': [
                {
                    'name': '焦文通部',
                    'faction': '宋军',
                    'commander': '焦文通',
                    'troop_type': 'mixed',
                    'troop_count': '数千',
                    'direction': '东南',
                },
                {
                    'name': '合扎猛安',
                    'faction': '金军',
                    'commander': '',
                    'troop_type': 'cavalry',
                    'troop_count': '一千骑',
                    'direction': '西北',
                },
            ],
            'unit_states': [
                {
                    'seq': 2,
                    'unit_name': '焦文通部',
                    'status': 'marching',
                    'location': '东坡塬',
                    'description': '侧翼包抄',
                },
                {
                    'seq': 3,
                    'unit_name': '焦文通部',
                    'status': 'routing',
                    'location': '东坡塬',
                    'description': '全军崩溃',
                },
                {
                    'seq': 3,
                    'unit_name': '合扎猛安',
                    'status': 'marching',
                    'location': '东坡塬',
                    'description': '铁骑冲击',
                },
            ],
            'scale': 'tactical',
        }
    )

    result = extract_timeline(TIMELINE_WITH_UNITS)
    assert isinstance(result, CampaignTimeline)
    assert len(result.units) == 2
    assert result.units[0].name == '焦文通部'
    assert result.units[1].troop_type == 'cavalry'
    assert len(result.unit_states) == 3
    # 验证状态
    assert result.unit_states[0].status == 'marching'
    assert result.unit_states[1].status == 'routing'


@patch('shaosongmap.extractor.OpenAI')
def test_extract_timeline_no_units_in_static_mode(mock_openai: MagicMock):
    """static 模式（不带 timeline 参数）也兼容 units 为空。"""
    mock_openai.return_value.chat.completions.create.return_value = _mock_response(
        {
            'campaign_name': None,
            'factions': [],
            'places': [],
            'routes': [],
            'events': [],
            'units': [],
            'unit_states': [],
        }
    )

    result = extract_timeline('一些文本')
    assert result.units == []
    assert result.unit_states == []


def test_unit_status_enum():
    """UnitStatus 枚举包含所有预期值。"""
    valid = {'deploying', 'marching', 'engaging', 'retreating', 'routing'}
    assert set(UnitStatus.__args__) == valid  # type: ignore[attr-defined]


def test_troop_type_enum():
    """TroopType 枚举包含所有预期值。"""
    assert set(TroopType.__args__) == {'infantry', 'cavalry', 'mixed'}  # type: ignore[attr-defined]
