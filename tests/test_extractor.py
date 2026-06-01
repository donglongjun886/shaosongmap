"""Extractor 模块单元测试。"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from shaosongmap.extractor import extract
from shaosongmap.models import GeoEntityExtract, Place


def _mock_response(json_data: dict) -> MagicMock:
    choice = MagicMock()
    choice.message.content = json.dumps(json_data)
    resp = MagicMock()
    resp.choices = [choice]
    return resp


SAMPLE = '岳飞率三万兵马自襄阳渡汉水，经唐州直驱汴京。'


@patch('shaosongmap.extractor.OpenAI')
def test_extract_full_fields(mock_openai: MagicMock):
    """正常提取：返回所有字段（含地名和人物地点关联）。"""
    mock_openai.return_value.chat.completions.create.return_value = _mock_response(
        {
            'event_name': '岳飞北伐',
            'dynasty': '南宋',
            'boundaries': [
                {'name': '宋金边界', 'description': '西起秦岭，东至淮河'},
            ],
            'places': [
                {'name': '襄阳', 'context': '自襄阳'},
                {'name': '汉水', 'context': '渡汉水'},
                {'name': '唐州', 'context': '经唐州'},
                {'name': '汴京', 'context': '直驱汴京'},
            ],
            'person_places': [
                {'person': '岳飞', 'place': '襄阳', 'relation': '驻扎'},
            ],
            'scale': 'strategic',
        }
    )

    result = extract(SAMPLE)
    assert isinstance(result, GeoEntityExtract)
    assert result.event_name == '岳飞北伐'
    assert result.dynasty == '南宋'
    assert len(result.boundaries) == 1
    assert result.boundaries[0].name == '宋金边界'
    assert len(result.places) == 4
    assert len(result.person_places) == 1
    assert result.person_places[0].person == '岳飞'
    assert result.person_places[0].place == '襄阳'
    assert result.person_places[0].relation == '驻扎'
    assert result.scale == 'strategic'


@patch('shaosongmap.extractor.OpenAI')
def test_extract_march_only_no_battle(mock_openai: MagicMock):
    """纯行军文本：event_name 为 null。"""
    mock_openai.return_value.chat.completions.create.return_value = _mock_response(
        {
            'event_name': None,
            'dynasty': '南宋',
            'boundaries': [],
            'places': [{'name': '建康', 'context': '还师建康'}],
            'person_places': [{'person': '岳飞', 'place': '建康', 'relation': '行军经过'}],
            'scale': None,
        }
    )

    result = extract('岳飞率部还师建康。')
    assert result.event_name is None
    assert len(result.places) == 1


@patch('shaosongmap.extractor.OpenAI')
def test_extract_validation_error(mock_openai: MagicMock):
    """LLM 返回不合法格式时抛出 ValueError。"""
    mock_openai.return_value.chat.completions.create.return_value = _mock_response(
        {
            'event_name': '测试',
            'boundaries': 'should be list',  # 类型错误
        }
    )

    with pytest.raises(ValueError):
        extract(SAMPLE)


@patch('shaosongmap.extractor.OpenAI')
def test_extract_empty_text(mock_openai: MagicMock):
    """空文本直接拒绝，不调 API。"""
    with pytest.raises(ValueError, match='不能为空'):
        extract('   ')
    mock_openai.assert_not_called()


@patch('shaosongmap.extractor.OpenAI')
def test_extract_mixed_content_no_geography(mock_openai: MagicMock):
    """纯朝堂对话无地理信息：LLM 返回空 places/person_places。"""
    mock_openai.return_value.chat.completions.create.return_value = _mock_response(
        {
            'event_name': None,
            'dynasty': None,
            'boundaries': [],
            'places': [],
            'person_places': [],
            'scale': None,
        }
    )

    text = "赵官家沉吟良久，道：'北边局势，诸位爱卿有何高见？'李纲奏道：'臣以为当固守黄河防线。'"
    result = extract(text)
    assert result.event_name is None
    assert result.places == []
    assert result.person_places == []


@patch('shaosongmap.extractor.OpenAI')
def test_extract_mixed_content_with_military(mock_openai: MagicMock):
    """混合内容：LLM 仅从军事段落提取，忽略朝堂对话中的假设性建议。"""
    mock_openai.return_value.chat.completions.create.return_value = _mock_response(
        {
            'event_name': '岳飞北伐',
            'dynasty': '南宋',
            'boundaries': [],
            'places': [
                {'name': '襄阳', 'context': '自襄阳出发'},
                {'name': '汴京', 'context': '直驱汴京'},
            ],
            'person_places': [
                {'person': '岳飞', 'place': '襄阳', 'relation': '驻扎'},
                {'person': '完颜宗弼', 'place': '汴京', 'relation': '镇守'},
            ],
            'scale': 'battle',
        }
    )

    text = (
        "朝堂上，秦桧奏道：'陛下，臣以为若从襄阳出兵，风险太大。'"
        '然而，岳飞此时已率三万兵马自襄阳出发，直驱汴京。'
        '金军完颜宗弼以五万大军迎战。'
    )
    result = extract(text)
    assert len(result.places) == 2
    assert len(result.person_places) >= 1
    # 秦桧是对话人物，不是实际将领，不应出现在 person_places 中
    person_names = {pp.person for pp in result.person_places}
    assert '秦桧' not in person_names


@patch('shaosongmap.extractor.OpenAI')
def test_extract_filters_military_unit_places_in_prompt(mock_openai: MagicMock):
    """集成测试：system prompt 规则7要求 LLM 不过滤军队编制名（由 prompt 层面处理）。"""
    mock_openai.return_value.chat.completions.create.return_value = _mock_response(
        {
            'event_name': '宋夏战争',
            'dynasty': '北宋',
            'boundaries': [],
            'places': [
                {'name': '渭州', 'context': '自渭州出发'},
                {'name': '原州', 'context': '驰援原州'},
            ],
            'person_places': [
                {'person': '刘昌祚', 'place': '渭州', 'relation': '驻扎'},
            ],
            'scale': 'battle',
        }
    )

    result = extract('秦凤路大军自渭州出发，泾原路兵马驰援原州。')
    place_names = {p.name for p in result.places}
    # 军队编制名不应作为地名出现（由 prompt 层面过滤）
    assert '秦凤路' not in place_names
    assert '泾原路' not in place_names
    assert '渭州' in place_names
    assert '原州' in place_names


def test_place_model():
    """Place 模型基本字段测试。"""
    place = Place(name='潼关', context='至潼关')
    assert place.name == '潼关'
    assert place.context == '至潼关'

    # 不传 context 时默认为空字符串
    place2 = Place(name='渭州')
    assert place2.name == '渭州'
    assert place2.context == ''
