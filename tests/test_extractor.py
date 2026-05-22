"""Extractor 模块单元测试。"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from shaosongmap.extractor import _filter_military_unit_places, extract
from shaosongmap.models import CampaignExtract, Place


def _mock_response(json_data: dict) -> MagicMock:
    choice = MagicMock()
    choice.message.content = json.dumps(json_data)
    resp = MagicMock()
    resp.choices = [choice]
    return resp


SAMPLE = "岳飞率三万兵马自襄阳渡汉水，经唐州直驱汴京。"


@patch("shaosongmap.extractor.OpenAI")
def test_extract_full_fields(mock_openai: MagicMock):
    """正常提取：返回所有字段。"""
    mock_openai.return_value.chat.completions.create.return_value = _mock_response({
        "campaign_name": "岳飞北伐",
        "factions": [
            {"name": "宋军", "commanders": ["岳飞"], "troops": "三万"},
            {"name": "金军", "commanders": [], "troops": None},
        ],
        "places": [
            {"name": "襄阳", "context": "自襄阳"},
            {"name": "汉水", "context": "渡汉水"},
            {"name": "唐州", "context": "经唐州"},
            {"name": "汴京", "context": "直驱汴京"},
        ],
        "routes": [
            {"from": "襄阳", "to": "汴京", "via": ["唐州"]},
        ],
        "scale": "battle",
    })

    result = extract(SAMPLE)
    assert isinstance(result, CampaignExtract)
    assert result.campaign_name == "岳飞北伐"
    assert len(result.factions) == 2
    assert result.factions[0].commanders == ["岳飞"]
    assert len(result.places) == 4
    assert len(result.routes) == 1
    assert result.scale == "battle"


@patch("shaosongmap.extractor.OpenAI")
def test_extract_march_only_no_battle(mock_openai: MagicMock):
    """纯行军文本：campaign_name 为 null。"""
    mock_openai.return_value.chat.completions.create.return_value = _mock_response({
        "campaign_name": None,
        "factions": [{"name": "宋军", "commanders": ["岳飞"], "troops": "三千"}],
        "places": [{"name": "建康", "context": "还师建康"}],
        "routes": [],
    })

    result = extract("岳飞率部还师建康。")
    assert result.campaign_name is None
    assert len(result.places) == 1


@patch("shaosongmap.extractor.OpenAI")
def test_extract_validation_error(mock_openai: MagicMock):
    """LLM 返回不合法格式时抛出 ValueError。"""
    mock_openai.return_value.chat.completions.create.return_value = _mock_response({
        "campaign_name": "测试",
        "factions": "should be list",  # 类型错误
    })

    with pytest.raises(ValueError):
        extract(SAMPLE)


@patch("shaosongmap.extractor.OpenAI")
def test_extract_empty_text(mock_openai: MagicMock):
    """空文本直接拒绝，不调 API。"""
    with pytest.raises(ValueError, match="不能为空"):
        extract("   ")
    mock_openai.assert_not_called()


@patch("shaosongmap.extractor.OpenAI")
def test_extract_mixed_content_no_military(mock_openai: MagicMock):
    """纯朝堂对话无军事行动：LLM 返回空 places/routes。"""
    mock_openai.return_value.chat.completions.create.return_value = _mock_response({
        "campaign_name": None,
        "factions": [{"name": "宋廷", "commanders": [], "troops": None}],
        "places": [],
        "routes": [],
    })

    text = "赵官家沉吟良久，道：'北边局势，诸位爱卿有何高见？'李纲奏道：'臣以为当固守黄河防线。'"
    result = extract(text)
    assert result.campaign_name is None
    assert result.places == []
    assert result.routes == []


@patch("shaosongmap.extractor.OpenAI")
def test_extract_mixed_content_with_military(mock_openai: MagicMock):
    """混合内容：LLM 仅从军事段落提取，忽略朝堂对话中的假设性建议。"""
    mock_openai.return_value.chat.completions.create.return_value = _mock_response({
        "campaign_name": "岳飞北伐",
        "factions": [
            {"name": "宋军", "commanders": ["岳飞"], "troops": "三万"},
            {"name": "金军", "commanders": ["完颜宗弼"], "troops": "五万"},
        ],
        "places": [
            {"name": "襄阳", "context": "自襄阳出发"},
            {"name": "汴京", "context": "直驱汴京"},
        ],
        "routes": [
            {"from": "襄阳", "to": "汴京"},
        ],
    })

    text = (
        "朝堂上，秦桧奏道：'陛下，臣以为若从襄阳出兵，风险太大。'"
        "然而，岳飞此时已率三万兵马自襄阳出发，直驱汴京。"
        "金军完颜宗弼以五万大军迎战。"
    )
    result = extract(text)
    assert len(result.places) == 2
    assert len(result.routes) == 1
    # 秦桧是对话人物，不是实际将领
    assert "秦桧" not in result.factions[0].commanders


# ── 军队编制名过滤测试 ──


class TestFilterMilitaryUnitPlaces:
    """后处理过滤函数单元测试。"""

    def test_filter_army_suffix_dajun(self):
        """「X路大军」模式中的地名应被过滤。"""
        places = [
            {"name": "秦凤路", "context": "秦凤路大军自渭州出发"},
            {"name": "渭州", "context": "自渭州出发"},
        ]
        result = _filter_military_unit_places(places)
        names = {p["name"] for p in result}
        assert "秦凤路" not in names
        assert "渭州" in names

    def test_filter_army_suffix_bingma(self):
        """「X路兵马」模式中的地名应被过滤。"""
        places = [
            {"name": "泾原路", "context": "泾原路兵马驰援"},
            {"name": "原州", "context": "驰援原州"},
        ]
        result = _filter_military_unit_places(places)
        names = {p["name"] for p in result}
        assert "泾原路" not in names
        assert "原州" in names

    def test_keep_standalone_place(self):
        """独立使用的地名应保留。"""
        places = [
            {"name": "秦凤路", "context": "大军自秦凤路出发，秦凤路境内多山地"},
        ]
        result = _filter_military_unit_places(places)
        assert len(result) == 1
        assert result[0]["name"] == "秦凤路"

    def test_filter_empty_context(self):
        """context 为空时不抛异常，保留该条目。"""
        places = [
            {"name": "某地", "context": ""},
        ]
        result = _filter_military_unit_places(places)
        assert len(result) == 1

    def test_filter_no_name(self):
        """name 为空时不抛异常，保留该条目。"""
        places = [
            {"name": "", "context": "大军出发"},
        ]
        result = _filter_military_unit_places(places)
        assert len(result) == 1

    def test_filter_multiple_military_patterns(self):
        """多种军队编制模式同时存在，全部过滤。"""
        places = [
            {"name": "环庆路", "context": "环庆路将士率先抵达"},
            {"name": "熙河路", "context": "熙河路各部随后跟进"},
            {"name": "鄜延路", "context": "鄜延路兵马断后"},
            {"name": "潼关", "context": "会师于潼关"},
        ]
        result = _filter_military_unit_places(places)
        names = {p["name"] for p in result}
        assert names == {"潼关"}  # 只有独立地名保留


@patch("shaosongmap.extractor.OpenAI")
def test_extract_filters_military_unit_places(mock_openai: MagicMock):
    """集成测试：extract() 返回前过滤军队编制名。"""
    mock_openai.return_value.chat.completions.create.return_value = _mock_response({
        "campaign_name": "宋夏战争",
        "factions": [
            {"name": "宋军", "commanders": ["刘昌祚"], "troops": "五万"},
            {"name": "夏军", "commanders": [], "troops": None},
        ],
        "places": [
            {"name": "秦凤路", "context": "秦凤路大军自渭州出发"},
            {"name": "泾原路", "context": "泾原路兵马驰援"},
            {"name": "渭州", "context": "自渭州出发"},
            {"name": "原州", "context": "驰援原州"},
        ],
        "routes": [
            {"from": "渭州", "to": "原州"},
        ],
    })

    result = extract("秦凤路大军自渭州出发，泾原路兵马驰援原州。")
    place_names = {p.name for p in result.places}
    assert "秦凤路" not in place_names
    assert "泾原路" not in place_names
    assert "渭州" in place_names
    assert "原州" in place_names


# ── scale 字段测试 ──


@patch("shaosongmap.extractor.OpenAI")
def test_extract_scale_tactical(mock_openai: MagicMock):
    """战术级：单次局部冲突应返回 tactical。"""
    mock_openai.return_value.chat.completions.create.return_value = _mock_response({
        "campaign_name": None,
        "factions": [
            {"name": "宋军", "commanders": ["焦文通"], "troops": "数千"},
            {"name": "金军", "commanders": ["蒲查胡盏"], "troops": "一千骑"},
        ],
        "places": [
            {"name": "东坡塬", "context": "从东坡塬上轮换下来"},
            {"name": "金粟山", "context": "金粟山下披挂整齐"},
            {"name": "塬地", "context": "贴着塬底"},
        ],
        "routes": [],
        "scale": "tactical",
    })

    result = extract("焦文通部在东坡塬遭遇金军铁浮屠冲击，全军崩溃。")
    assert result.scale == "tactical"


@patch("shaosongmap.extractor.OpenAI")
def test_extract_scale_strategic(mock_openai: MagicMock):
    """战略级：跨多路大军应返回 strategic。"""
    mock_openai.return_value.chat.completions.create.return_value = _mock_response({
        "campaign_name": "宋金富平会战",
        "factions": [
            {"name": "宋军", "commanders": ["张浚", "刘锡", "吴玠"], "troops": "十八万"},
            {"name": "金军", "commanders": ["完颜宗弼", "完颜娄室"], "troops": None},
        ],
        "places": [
            {"name": "秦凤路", "context": "秦凤路出兵"},
            {"name": "泾原路", "context": "泾原路出兵"},
            {"name": "环庆路", "context": "环庆路出兵"},
            {"name": "熙河路", "context": "熙河路出兵"},
            {"name": "富平", "context": "会战于富平"},
        ],
        "routes": [
            {"from": "秦凤路", "to": "富平"},
            {"from": "泾原路", "to": "富平"},
        ],
        "scale": "strategic",
    })

    result = extract("张浚调五路大军会战于富平。")
    assert result.scale == "strategic"


@patch("shaosongmap.extractor.OpenAI")
def test_extract_scale_invalid(mock_openai: MagicMock):
    """非法 scale 值应触发 ValidationError。"""
    mock_openai.return_value.chat.completions.create.return_value = _mock_response({
        "campaign_name": "测试",
        "factions": [],
        "places": [],
        "routes": [],
        "scale": "continental",
    })

    with pytest.raises(ValueError):
        extract("测试文本。")


def test_place_type_field():
    """Place 模型接受 place_type 字段。"""
    place = Place(name="潼关", context="至潼关", place_type="mountain_pass")
    assert place.place_type == "mountain_pass"

    # 不传 place_type 时默认为 None
    place2 = Place(name="渭州", context="自渭州")
    assert place2.place_type is None


def test_place_type_validation():
    """place_type 仅接受枚举值。"""
    with pytest.raises(ValueError):
        Place(name="测试", context="测试", place_type="invalid_type")
