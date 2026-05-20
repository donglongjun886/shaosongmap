"""OCR API 端点测试。"""

from __future__ import annotations

import io
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app import app

client = TestClient(app)


def _make_fake_png() -> bytes:
    """生成一张最小的有效 PNG 图片。"""
    img = Image.new("RGB", (100, 100), color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.read()


@patch("app.ocr_main")
def test_ocr_success(mock_ocr):
    """正常上传 PNG 返回清洗文本。"""
    mock_text = "岳飞率三万兵马自襄阳渡汉水，经唐州、邓州，直驱汴京。金军完颜宗弼以五万大军据守朱仙镇，两军对峙于汴京城南。"
    mock_ocr.return_value = (mock_text, 15)

    resp = client.post(
        "/api/ocr",
        files={"file": ("screenshot.png", _make_fake_png(), "image/png")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "岳飞" in data["text"]
    assert len(data["text"]) >= 50


def test_ocr_wrong_format():
    """非 PNG/JPEG 文件返回 400。"""
    resp = client.post(
        "/api/ocr",
        files={"file": ("test.gif", b"GIF89a", "image/gif")},
    )
    assert resp.status_code == 400
    assert "PNG" in resp.json()["detail"]


def test_ocr_empty_file():
    """空图片返回 400。"""
    resp = client.post(
        "/api/ocr",
        files={"file": ("empty.png", b"", "image/png")},
    )
    assert resp.status_code == 400
    assert "不能为空" in resp.json()["detail"]


@patch("app.ocr_main")
def test_ocr_insufficient_text(mock_ocr):
    """OCR 文本不足 50 字返回 422。"""
    mock_ocr.side_effect = ValueError("未能从截图中提取到足够的文本（仅 15 字符）")

    resp = client.post(
        "/api/ocr",
        files={"file": ("blur.png", _make_fake_png(), "image/png")},
    )
    assert resp.status_code == 422
    assert "足够的文本" in resp.json()["detail"]
