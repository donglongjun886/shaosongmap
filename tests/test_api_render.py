"""/api/v1/render 端点测试。"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app import app

client = TestClient(app)


def test_render_success():
    """正常修正数据后重新渲染返回 GeoJSON。"""
    resp = client.post(
        '/api/v1/render',
        json={
            'event_name': '测试战役',
            'dynasty': None,
            'boundaries': [
                {'name': '宋金边界', 'description': '淮河一线'},
            ],
            'places': [
                {'name': '襄阳', 'context': '自襄阳出发'},
                {'name': '汴京', 'context': '直驱汴京'},
            ],
            'person_places': [
                {'person': '岳飞', 'place': '襄阳', 'relation': '驻扎'},
                {'person': '完颜宗弼', 'place': '汴京', 'relation': '镇守'},
            ],
            'scale': 'battle',
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert 'extract_id' in data
    assert data['event_name'] == '测试战役'
    assert len(data['boundaries']) == 1
    assert len(data['features']) == 2
    assert len(data['person_places']) == 2
    assert data['geojson']['type'] == 'FeatureCollection'
    assert data['scale'] == 'battle'


def test_render_empty_places():
    """无地名时正常返回空列表。"""
    resp = client.post(
        '/api/v1/render',
        json={
            'dynasty': None,
            'boundaries': [{'name': '宋金边界', 'description': '淮河'}],
            'places': [],
            'person_places': [],
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data['features'] == []


def test_render_invalid_types():
    """请求体字段类型错误返回 422。"""
    resp = client.post(
        '/api/v1/render',
        json={
            'places': 'not a list',
        },
    )
    assert resp.status_code == 422


def test_render_single_place():
    """单地名正常返回。"""
    resp = client.post(
        '/api/v1/render',
        json={
            'dynasty': None,
            'boundaries': [],
            'places': [{'name': '襄阳', 'context': ''}],
            'person_places': [],
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data['features']) == 1
    assert data['geojson']['type'] == 'FeatureCollection'
