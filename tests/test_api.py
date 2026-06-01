"""API 集成测试（单次请求/响应格式）。"""

from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient

from app import app

client = TestClient(app)


def _patch_pipeline_result():
    """模拟 run_extract_pipeline 返回的完整结果字典。"""
    return {
        'extract_id': 'test123456',
        'event_name': '岳飞北伐',
        'boundaries': [
            {'name': '宋金边界', 'description': '淮河一线'},
        ],
        'person_places': [
            {'person': '岳飞', 'place': '襄阳', 'relation': '驻扎'},
            {'person': '完颜宗弼', 'place': '汴京', 'relation': '镇守'},
        ],
        'features': [],
        'geojson': {'type': 'FeatureCollection', 'features': []},
        'scale': 'battle',
    }


def _error_msg(resp):
    data = resp.json()
    if isinstance(data.get('error'), dict):
        return data['error'].get('message', '')
    if isinstance(data.get('detail'), dict) and isinstance(data['detail'].get('error'), dict):
        return data['detail']['error'].get('message', '')
    return str(data.get('detail', ''))


def test_api_extract_success():
    with patch(
        'shaosongmap.routers.extract.run_extract_pipeline',
        return_value=_patch_pipeline_result(),
    ):
        resp = client.post(
            '/api/v1/extract',
            json={'text': '岳飞率三万兵马自襄阳经唐州直驱汴京。'},
        )
    assert resp.status_code == 200
    assert resp.headers['content-type'].startswith('application/json')
    data = resp.json()
    assert 'extract_id' in data
    assert data['event_name'] == '岳飞北伐'
    assert len(data['boundaries']) == 1
    assert len(data['person_places']) == 2
    assert data['geojson']['type'] == 'FeatureCollection'


def test_api_extract_empty_text():
    resp = client.post('/api/v1/extract', json={'text': '   '})
    assert resp.status_code == 422
    assert '不能为空' in _error_msg(resp)


def test_api_extract_with_dynasty():
    with patch(
        'shaosongmap.routers.extract.run_extract_pipeline',
        return_value=_patch_pipeline_result(),
    ):
        resp = client.post(
            '/api/v1/extract',
            json={'text': '宋军北伐', 'dynasty': '北宋'},
        )
    assert resp.status_code == 200
    assert resp.headers['content-type'].startswith('application/json')
    data = resp.json()
    assert data['event_name'] == '岳飞北伐'


def test_api_extract_llm_error():
    with patch(
        'shaosongmap.routers.extract.run_extract_pipeline',
        side_effect=ValueError('DeepSeek API 返回空响应'),
    ):
        resp = client.post('/api/v1/extract', json={'text': '测试'})
    assert resp.status_code == 422
    assert '返回空' in _error_msg(resp)


def test_static_page():
    resp = client.get('/')
    assert resp.status_code == 200
    assert 'ShaosongMap' in resp.text
