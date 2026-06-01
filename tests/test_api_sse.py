"""提取端点单次请求/响应格式测试。"""

from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient

from app import app

client = TestClient(app)


def _patch_pipeline():
    return {
        'extract_id': 'test123456',
        'event_name': '测试战役',
        'boundaries': [{'name': '宋金边界', 'description': '淮河防线'}],
        'person_places': [{'person': '岳飞', 'place': '襄阳', 'relation': '驻扎'}],
        'features': [],
        'geojson': {'type': 'FeatureCollection', 'features': []},
        'scale': 'battle',
    }


def test_extract_single_response():
    """单次请求返回 JSON 响应（非 SSE 流）。"""
    # 模拟完整管道结果
    with patch(
        'shaosongmap.routers.extract.run_extract_pipeline',
        return_value=_patch_pipeline(),
    ):
        resp = client.post('/api/v1/extract', json={'text': '测试文本'})
        assert resp.status_code == 200
        assert resp.headers['content-type'].startswith('application/json')

        data = resp.json()
        assert 'extract_id' in data
        assert 'event_name' in data
        assert 'boundaries' in data
        assert 'person_places' in data
        assert 'features' in data
        assert 'geojson' in data
        assert data['geojson']['type'] == 'FeatureCollection'


def test_extract_geocode_error_handling():
    """管道内部异常通过 422 错误响应返回。"""
    with patch(
        'shaosongmap.routers.extract.run_extract_pipeline',
        side_effect=ValueError('CHGIS 数据不可用'),
    ):
        resp = client.post('/api/v1/extract', json={'text': '测试文本'})
        assert resp.status_code == 422
        data = resp.json()
        assert 'CHGIS 数据不可用' in data['error']['message']
