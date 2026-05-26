"""SSE 端点事件流格式测试。"""

from __future__ import annotations

import contextlib
import json
from unittest.mock import patch

from fastapi.testclient import TestClient

from app import app

client = TestClient(app)


def _patch_extract():
    from shaosongmap.models import CampaignExtract, Faction, Place, Route

    return CampaignExtract(
        campaign_name='测试战役',
        factions=[Faction(name='宋军', commanders=['岳飞'], troops='三万')],
        places=[Place(name='襄阳', context='')],
        routes=[Route(from_place='襄阳', to_place='汴京', via=[])],
    )


def _parse_events(body: str) -> list[tuple[str, dict]]:
    events = []
    event_type = ''
    for line in body.split('\n'):
        if line.startswith('event: '):
            event_type = line[7:]
        elif line.startswith('data: '):
            with contextlib.suppress(json.JSONDecodeError):
                events.append((event_type, json.loads(line[6:])))
            event_type = ''
    return events


@patch('shaosongmap.services.pipeline.extract')
def test_sse_event_format(mock_extract):
    """SSE 流包含正确的事件类型序列。"""
    mock_extract.return_value = _patch_extract()

    resp = client.post('/api/v1/extract', json={'text': '测试文本'})
    assert resp.status_code == 200
    assert resp.headers['content-type'].startswith('text/event-stream')
    assert resp.headers['cache-control'] == 'no-cache'
    assert resp.headers['x-accel-buffering'] == 'no'

    events = _parse_events(resp.text)
    event_types = [t for t, _ in events]
    # 应有至少 3 个 progress + 1 个 result
    assert event_types.count('progress') == 3
    assert 'result' in event_types

    # 按顺序检查阶段名称
    progress_events = [d for t, d in events if t == 'progress']
    stages = [d['stage'] for d in progress_events]
    assert stages == ['extract_done', 'geocode_done', 'render_done']

    # 每个 progress 有 ok: true
    for d in progress_events:
        assert d['ok'] is True
        assert 'detail' in d


@patch('shaosongmap.services.pipeline.extract')
def test_sse_result_contains_all_fields(mock_extract):
    """Result 事件包含完整的响应字段。"""
    mock_extract.return_value = _patch_extract()

    resp = client.post('/api/v1/extract', json={'text': '测试文本'})
    events = _parse_events(resp.text)
    result = next(d for t, d in events if t == 'result')
    assert 'extract_id' in result
    assert 'campaign_name' in result
    assert 'factions' in result
    assert 'features' in result
    assert 'routes' in result
    assert 'geojson' in result
    assert result['geojson']['type'] == 'FeatureCollection'


@patch('shaosongmap.services.pipeline.extract')
def test_sse_geocode_error_handling(mock_extract):
    """Geocode 阶段异常通过 SSE error 事件返回。"""
    mock_extract.return_value = _patch_extract()

    # 模拟 geocode 失败：传入非法数据导致异常
    with patch('shaosongmap.services.pipeline.geocode', side_effect=Exception('CHGIS 数据不可用')):
        resp = client.post('/api/v1/extract', json={'text': '测试文本'})
        events = _parse_events(resp.text)

        # 第一个是 extract_done progress
        assert events[0][0] == 'progress'
        assert events[0][1]['stage'] == 'extract_done'

        # 第二个是 geocode error
        error_events = [e for e in events if e[0] == 'error']
        assert len(error_events) == 1
        assert error_events[0][1]['stage'] == 'geocode'
        assert 'CHGIS 数据不可用' in error_events[0][1]['message']
