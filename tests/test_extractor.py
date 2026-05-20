"""Extractor 模块单元测试。"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from shaosongmap.extractor import extract
from shaosongmap.models import CampaignExtract


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
    })

    result = extract(SAMPLE)
    assert isinstance(result, CampaignExtract)
    assert result.campaign_name == "岳飞北伐"
    assert len(result.factions) == 2
    assert result.factions[0].commanders == ["岳飞"]
    assert len(result.places) == 4
    assert len(result.routes) == 1


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
