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
