"""/api/render 端点测试。"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app import app

client = TestClient(app)


def test_render_success():
    """正常修正数据后重新渲染返回 GeoJSON。"""
    resp = client.post(
        '/api/render',
        json={
            'campaign_name': '测试战役',
            'factions': [
                {'name': '宋军', 'commanders': ['岳飞'], 'troops': '三万'},
                {'name': '金军', 'commanders': ['完颜宗弼'], 'troops': '五万'},
            ],
            'places': [
                {'name': '襄阳', 'context': '自襄阳出发'},
                {'name': '汴京', 'context': '直驱汴京'},
            ],
            'routes': [
                {'from': '襄阳', 'to': '汴京'},
            ],
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert 'extract_id' in data
    assert data['campaign_name'] == '测试战役'
    assert len(data['factions']) == 2
    assert len(data['features']) == 2
    assert data['geojson']['type'] == 'FeatureCollection'


def test_render_empty_places():
    """无地名时正常返回空列表。"""
    resp = client.post(
        '/api/render',
        json={
            'factions': [{'name': '宋军', 'commanders': ['岳飞'], 'troops': '三万'}],
            'places': [],
            'routes': [],
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data['features'] == []
    assert data['routes'] == []


def test_render_invalid_types():
    """请求体字段类型错误返回 422。"""
    resp = client.post(
        '/api/render',
        json={
            'places': 'not a list',
            'routes': 'not a list',
        },
    )
    assert resp.status_code == 422


def test_render_no_routes():
    """无行军路线时正常返回。"""
    resp = client.post(
        '/api/render',
        json={
            'factions': [],
            'places': [{'name': '襄阳', 'context': ''}],
            'routes': [],
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data['features']) == 1
    assert data['routes'] == []
