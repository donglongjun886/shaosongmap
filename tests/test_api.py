"""API 集成测试。"""

from __future__ import annotations

import json
from unittest.mock import patch

from fastapi.testclient import TestClient

from app import app

client = TestClient(app)


_mock_campaign = {
    'campaign_name': '岳飞北伐',
    'factions': [
        {'name': '宋军', 'commanders': ['岳飞'], 'troops': '三万'},
        {'name': '金军', 'commanders': ['完颜宗弼'], 'troops': '五万'},
    ],
    'places': [
        {'name': '襄阳', 'context': '自襄阳'},
        {'name': '唐州', 'context': '经唐州'},
        {'name': '汴京', 'context': '直驱汴京'},
    ],
    'routes': [{'from': '襄阳', 'to': '汴京', 'via': ['唐州']}],
}


def _patch_extract():
    from shaosongmap.models import CampaignExtract, Faction, Place, Route

    return CampaignExtract(
        campaign_name='岳飞北伐',
        factions=[
            Faction(name='宋军', commanders=['岳飞'], troops='三万'),
            Faction(name='金军', commanders=['完颜宗弼'], troops='五万'),
        ],
        places=[
            Place(name='襄阳', context='自襄阳'),
            Place(name='唐州', context='经唐州'),
            Place(name='汴京', context='直驱汴京'),
        ],
        routes=[Route(from_place='襄阳', to_place='汴京', via=['唐州'])],
    )


def _parse_sse(body: str) -> list[tuple[str, dict]]:
    """解析 SSE 响应体，返回 [(event_type, data_dict), ...] 列表。"""
    events = []
    event_type = ''
    for line in body.split('\n'):
        if line.startswith('event: '):
            event_type = line[7:]
        elif line.startswith('data: '):
            try:
                data = json.loads(line[6:])
            except json.JSONDecodeError:
                continue
            events.append((event_type, data))
            event_type = ''
    return events


@patch('app.extract')
def test_api_extract_success(mock_extract):
    """正常请求返回 SSE 流，最终包含 result 事件和 GeoJSON。"""
    mock_extract.return_value = _patch_extract()

    resp = client.post(
        '/api/extract',
        json={
            'text': '岳飞率三万兵马自襄阳经唐州直驱汴京。',
        },
    )
    assert resp.status_code == 200
    assert resp.headers['content-type'].startswith('text/event-stream')

    events = _parse_sse(resp.text)
    event_types = [t for t, _ in events]
    assert 'progress' in event_types
    assert 'result' in event_types

    result = next(d for t, d in events if t == 'result')
    assert 'extract_id' in result
    assert result['campaign_name'] == '岳飞北伐'
    assert len(result['factions']) == 2
    assert len(result['features']) == 3
    assert result['geojson']['type'] == 'FeatureCollection'


def test_api_extract_empty_text():
    """空文本返回 422（前置校验，不启动 SSE 流）。"""
    resp = client.post('/api/extract', json={'text': '   '})
    assert resp.status_code == 422
    assert '不能为空' in resp.json()['detail']


@patch('app.extract')
def test_api_extract_with_dynasty(mock_extract):
    """带朝代参数正常返回 SSE 流。"""
    mock_extract.return_value = _patch_extract()
    resp = client.post(
        '/api/extract',
        json={
            'text': '宋军北伐',
            'dynasty': '北宋',
        },
    )
    assert resp.status_code == 200
    assert 'text/event-stream' in resp.headers['content-type']
    events = _parse_sse(resp.text)
    assert any(t == 'result' for t, _ in events)


@patch('app.extract')
def test_api_extract_llm_error(mock_extract):
    """Extractor 异常通过 SSE error 事件返回。"""
    mock_extract.side_effect = ValueError('DeepSeek API 返回空响应')
    resp = client.post('/api/extract', json={'text': '测试'})
    assert resp.status_code == 200  # SSE 流已建立
    events = _parse_sse(resp.text)
    assert len(events) == 1
    event_type, data = events[0]
    assert event_type == 'error'
    assert data['stage'] == 'extract'
    assert '返回空' in data['message']


def test_static_page():
    """静态页面可正常访问。"""
    resp = client.get('/')
    assert resp.status_code == 200
    assert 'ShaosongMap' in resp.text
