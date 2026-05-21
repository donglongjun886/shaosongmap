"""Timeline 提取器模块单元测试。"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from shaosongmap.extractor import extract_timeline
from shaosongmap.models import CampaignTimeline, TimelineEvent


def _mock_response(json_data: dict) -> MagicMock:
    choice = MagicMock()
    choice.message.content = json.dumps(json_data)
    resp = MagicMock()
    resp.choices = [choice]
    return resp


TIMELINE_SAMPLE = (
    "岳飞率三万兵马自襄阳出发，渡汉水后向东北行军。"
    "数日后抵达唐州，遭遇金军斥候发生小规模冲突。"
    "岳家军乘胜追击，在蔡州与张宪部会合扎营休整。"
    "最终在朱仙镇与金军完颜宗弼决战，金军溃败撤退。"
)


@patch("shaosongmap.extractor.OpenAI")
def test_extract_timeline_full_sequence(mock_openai: MagicMock):
    """正常提取：返回完整事件序列（行军→战斗→扎营→决战→撤退）。"""
    mock_openai.return_value.chat.completions.create.return_value = _mock_response({
        "campaign_name": "岳飞北伐",
        "factions": [
            {"name": "宋军", "commanders": ["岳飞", "张宪"], "troops": "三万"},
            {"name": "金军", "commanders": ["完颜宗弼"], "troops": None},
        ],
        "places": [
            {"name": "襄阳", "context": "自襄阳出发"},
            {"name": "汉水", "context": "渡汉水"},
            {"name": "唐州", "context": "抵达唐州"},
            {"name": "蔡州", "context": "在蔡州"},
            {"name": "朱仙镇", "context": "在朱仙镇"},
        ],
        "routes": [
            {"from": "襄阳", "to": "朱仙镇", "via": ["唐州", "蔡州"]},
        ],
        "events": [
            {
                "seq": 1,
                "event_type": "march",
                "description": "岳飞率军从襄阳出发，渡汉水后向东北行军",
                "actors": ["岳飞", "岳家军"],
                "places_involved": ["襄阳", "汉水"],
            },
            {
                "seq": 2,
                "event_type": "battle",
                "description": "在唐州遭遇金军斥候，发生小规模冲突",
                "actors": ["岳飞", "金军斥候"],
                "places_involved": ["唐州"],
            },
            {
                "seq": 3,
                "event_type": "encamp",
                "description": "在蔡州与张宪部会合，扎营休整",
                "actors": ["岳飞", "张宪"],
                "places_involved": ["蔡州"],
            },
            {
                "seq": 4,
                "event_type": "battle",
                "description": "在朱仙镇与金军完颜宗弼决战",
                "actors": ["岳飞", "完颜宗弼"],
                "places_involved": ["朱仙镇"],
            },
            {
                "seq": 5,
                "event_type": "retreat",
                "description": "金军溃败撤退",
                "actors": ["完颜宗弼", "金军"],
                "places_involved": ["朱仙镇"],
            },
        ],
    })

    result = extract_timeline(TIMELINE_SAMPLE)
    assert isinstance(result, CampaignTimeline)
    assert result.campaign_name == "岳飞北伐"
    assert len(result.places) == 5
    assert len(result.routes) == 1
    assert len(result.events) == 5

    # 验证事件序列结构
    assert result.events[0].seq == 1
    assert result.events[0].event_type == "march"
    assert result.events[0].description
    assert "岳飞" in result.events[0].actors
    assert "襄阳" in result.events[0].places_involved

    assert result.events[1].event_type == "battle"
    assert result.events[2].event_type == "encamp"
    assert result.events[4].event_type == "retreat"

    # 事件地名应为 places 中的地名
    all_place_names = {p.name for p in result.places}
    for event in result.events:
        for place_name in event.places_involved:
            assert place_name in all_place_names


@patch("shaosongmap.extractor.OpenAI")
def test_extract_timeline_empty_no_military(mock_openai: MagicMock):
    """纯朝堂对话无军事行动：events 为空数组。"""
    mock_openai.return_value.chat.completions.create.return_value = _mock_response({
        "campaign_name": None,
        "factions": [{"name": "宋廷", "commanders": [], "troops": None}],
        "places": [],
        "routes": [],
        "events": [],
    })

    text = "赵官家沉吟良久，道：'北边局势，诸位爱卿有何高见？'"
    result = extract_timeline(text)
    assert isinstance(result, CampaignTimeline)
    assert result.events == []


def test_timeline_model_validation():
    """Pydantic 校验：非法 events 数据抛出 ValidationError。"""
    # 缺少必填字段 seq
    with pytest.raises(ValueError):
        CampaignTimeline.model_validate({
            "campaign_name": "测试",
            "factions": [],
            "places": [],
            "routes": [],
            "events": [
                {"event_type": "march", "description": "行军"},
            ],
        })

    # event_type 不合法
    with pytest.raises(ValueError):
        CampaignTimeline.model_validate({
            "campaign_name": "测试",
            "factions": [],
            "places": [],
            "routes": [],
            "events": [
                {"seq": 1, "event_type": "unknown_type", "description": "测试"},
            ],
        })


def test_extract_timeline_empty_text():
    """空文本直接拒绝，不调 API。"""
    with pytest.raises(ValueError, match="不能为空"):
        extract_timeline("   ")