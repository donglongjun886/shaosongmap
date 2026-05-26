"""Prometheus 指标定义：HTTP 请求、OCR 耗时。"""

from prometheus_client import Counter, Histogram, generate_latest
from prometheus_client.registry import CollectorRegistry

REGISTRY = CollectorRegistry(auto_describe=True)

http_requests_total = Counter(
    'http_requests_total',
    'HTTP 请求总数',
    ['method', 'endpoint', 'status'],
    registry=REGISTRY,
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP 请求延迟（秒）',
    ['method', 'endpoint'],
    buckets=[0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
    registry=REGISTRY,
)

ocr_duration_seconds = Histogram(
    'ocr_duration_seconds',
    'OCR 处理耗时（秒）',
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
    registry=REGISTRY,
)

ocr_errors_total = Counter(
    'ocr_errors_total',
    'OCR 处理错误次数',
    registry=REGISTRY,
)

extraction_duration_seconds = Histogram(
    'extraction_duration_seconds',
    '提取管道总耗时（秒）',
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0],
    registry=REGISTRY,
)


def get_metrics() -> bytes:
    """返回 Prometheus 文本格式的指标数据。"""
    return generate_latest(REGISTRY)  # type: ignore[no-any-return]
