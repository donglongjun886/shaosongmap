"""API 集成测试。"""

from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient

from app import app

client = TestClient(app)


_mock_campaign = {
    "campaign_name": "岳飞北伐",
    "factions": [
        {"name": "宋军", "commanders": ["岳飞"], "troops": "三万"},
        {"name": "金军", "commanders": ["完颜宗弼"], "troops": "五万"},
    ],
    "places": [
        {"name": "襄阳", "context": "自襄阳"},
        {"name": "唐州", "context": "经唐州"},
        {"name": "汴京", "context": "直驱汴京"},
    ],
    "routes": [{"from": "襄阳", "to": "汴京", "via": ["唐州"]}],
}


def _patch_extract():
    from shaosongmap.models import CampaignExtract, Faction, Place, Route
    return CampaignExtract(
        campaign_name="岳飞北伐",
        factions=[
            Faction(name="宋军", commanders=["岳飞"], troops="三万"),
            Faction(name="金军", commanders=["完颜宗弼"], troops="五万"),
        ],
        places=[
            Place(name="襄阳", context="自襄阳"),
            Place(name="唐州", context="经唐州"),
            Place(name="汴京", context="直驱汴京"),
        ],
        routes=[Route(from_place="襄阳", to_place="汴京", via=["唐州"])],
    )


@patch("app.extract")
def test_api_extract_success(mock_extract):
    """正常请求返回 200 + GeoJSON。"""
    mock_extract.return_value = _patch_extract()

    resp = client.post("/api/extract", json={
        "text": "岳飞率三万兵马自襄阳经唐州直驱汴京。",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "extract_id" in data
    assert data["campaign_name"] == "岳飞北伐"
    assert len(data["factions"]) == 2
    assert len(data["features"]) == 3
    assert data["geojson"]["type"] == "FeatureCollection"


@patch("app.extract")
def test_api_extract_empty_text(mock_extract):
    """空文本返回 422。"""
    mock_extract.side_effect = ValueError("战役文本不能为空")
    resp = client.post("/api/extract", json={"text": "   "})
    assert resp.status_code == 422


@patch("app.extract")
def test_api_extract_with_dynasty(mock_extract):
    """带朝代参数正常返回。"""
    mock_extract.return_value = _patch_extract()
    resp = client.post("/api/extract", json={
        "text": "宋军北伐", "dynasty": "北宋",
    })
    assert resp.status_code == 200


@patch("app.extract")
def test_api_extract_llm_error(mock_extract):
    """Extractor 异常返回 422。"""
    mock_extract.side_effect = ValueError("DeepSeek API 返回空响应")
    resp = client.post("/api/extract", json={"text": "测试"})
    assert resp.status_code == 422
    assert "返回空" in resp.json()["detail"]


def test_static_page():
    """静态页面可正常访问。"""
    resp = client.get("/")
    assert resp.status_code == 200
    assert "ShaosongMap" in resp.text
