"""批量 OCR API 端点测试。"""

from __future__ import annotations

import io
from unittest.mock import patch

from fastapi.testclient import TestClient
from PIL import Image

from app import app

client = TestClient(app)


def _make_fake_png() -> bytes:
    """生成一张最小的有效 PNG 图片。"""
    img = Image.new('RGB', (100, 100), color='white')
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return buf.read()


def _make_files(count: int) -> list:
    """生成指定数量的测试文件元组。"""
    return [('files', (f'screenshot_{i}.png', _make_fake_png(), 'image/png')) for i in range(count)]


@patch('app.ocr_main')
def test_batch_success(mock_ocr):
    """批量上传 3 张截图，返回拼接后文本。"""
    mock_ocr.side_effect = [
        ('第一章刘备率军西进', 5),
        ('率军西进抵达汉中诸葛亮献策', 5),
        ('诸葛亮献策后大军分三路出发', 5),
    ]

    resp = client.post('/api/ocr/batch', files=_make_files(3))
    assert resp.status_code == 200

    body = resp.text
    assert 'event: progress' in body
    assert 'event: merge' in body
    assert 'event: complete' in body
    assert 'removed_dup' in body


def test_batch_too_many_files():
    """上传超过 10 张返回 400。"""
    resp = client.post('/api/ocr/batch', files=_make_files(11))
    assert resp.status_code == 400
    assert '最多' in resp.json()['detail']


def test_batch_empty():
    """上传 0 张返回 422（FastAPI 校验 files 必填）。"""
    resp = client.post('/api/ocr/batch', files=[])
    assert resp.status_code == 422


def test_batch_wrong_format():
    """批量中某张格式错误返回 400（流式前校验）。"""
    files = [
        ('files', ('ok.png', _make_fake_png(), 'image/png')),
        ('files', ('bad.gif', b'GIF89a', 'image/gif')),
    ]
    resp = client.post('/api/ocr/batch', files=files)
    assert resp.status_code == 400
    assert '格式不支持' in resp.json()['detail']


def test_batch_oversized():
    """批量中某张超过 10MB 返回 413（流式前校验）。"""
    files = [
        ('files', ('ok.png', _make_fake_png(), 'image/png')),
        ('files', ('big.png', b'x' * (10 * 1024 * 1024 + 1), 'image/png')),
    ]
    resp = client.post('/api/ocr/batch', files=files)
    assert resp.status_code == 413
    assert '超过' in resp.json()['detail']


def test_batch_empty_file():
    """批量中某张为空返回 400（流式前校验）。"""
    files = [
        ('files', ('ok.png', _make_fake_png(), 'image/png')),
        ('files', ('empty.png', b'', 'image/png')),
    ]
    resp = client.post('/api/ocr/batch', files=files)
    assert resp.status_code == 400
    assert '不能为空' in resp.json()['detail']


@patch('app.ocr_main')
def test_batch_ocr_failure(mock_ocr):
    """某张截图 OCR 识别失败（文本不足）返回 SSE 错误事件。"""
    mock_ocr.side_effect = [
        ('第一章正常文本内容足够长可以识别', 5),
        ValueError('未能提取到足够的文字'),
    ]

    files = [
        ('files', ('good.png', _make_fake_png(), 'image/png')),
        ('files', ('bad.png', _make_fake_png(), 'image/png')),
    ]
    resp = client.post('/api/ocr/batch', files=files)
    assert resp.status_code == 200
    body = resp.text
    assert 'event: error' in body
    assert '第 2 张' in body


@patch('app.ocr_main')
def test_batch_progress_sequence(mock_ocr):
    """验证 SSE 事件按正确顺序推送。"""
    mock_ocr.side_effect = [
        ('文本片段一包含了足够的中文字符内容', 3),
        ('文本片段二也包含了足够的中文字符内容', 3),
    ]

    resp = client.post('/api/ocr/batch', files=_make_files(2))
    assert resp.status_code == 200
    body = resp.text

    events = []
    for line in body.split('\n'):
        if line.startswith('event: '):
            events.append(line[7:])

    assert events[0] == 'progress'
    assert events[1] == 'progress'
    assert events[2] == 'merge'
    assert events[3] == 'complete'
