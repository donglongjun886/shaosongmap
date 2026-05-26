# Observability Metrics 可观测性指标

## Purpose

定义 Prometheus 指标暴露规范，包括 HTTP 请求指标、OCR 处理指标和 /metrics 端点。

## Requirements

### Requirement: Prometheus /metrics 端点

系统 SHALL 在 `/metrics` 路径暴露 Prometheus 格式的指标端点。

端点 MUST：
- 返回 `Content-Type: text/plain; version=0.0.4` 的 Prometheus 文本格式
- 无需鉴权（设计为内网使用）
- 自动收集 HTTP 请求和 OCR 处理指标

#### Scenario: 指标端点可访问

- **WHEN** 客户端 GET `/metrics`
- **THEN** 返回 200，包含 `http_requests_total`、`http_request_duration_seconds` 等指标

#### Scenario: 指标不暴露敏感信息

- **WHEN** 客户端 GET `/metrics`
- **THEN** 响应中不包含 API key、用户数据等敏感信息

### Requirement: HTTP 请求指标

系统 MUST 自动为每个 HTTP 请求记录以下 Prometheus 指标：

- `http_requests_total{method, endpoint, status}` — Counter，统计请求总数
- `http_request_duration_seconds{method, endpoint}` — Histogram，统计请求延迟

Histogram 的 bucket SHALL 包含：`[0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]`（秒）。

#### Scenario: 正常请求计数

- **WHEN** 客户端 GET `/api/v1/extract` 返回 200
- **THEN** `http_requests_total{method="GET", endpoint="/api/v1/extract", status="200"}` 增加 1

#### Scenario: 错误请求计数

- **WHEN** 客户端 POST `/api/v1/extract` 返回 422
- **THEN** `http_requests_total{method="POST", endpoint="/api/v1/extract", status="422"}` 增加 1

### Requirement: OCR 处理指标

系统 MUST 记录 OCR 处理相关的指标：

- `ocr_duration_seconds` — Histogram，统计单次 OCR 处理耗时
- `ocr_errors_total` — Counter，统计 OCR 处理错误次数

#### Scenario: OCR 处理耗时记录

- **WHEN** 一次 OCR 识别完成
- **THEN** `ocr_duration_seconds` histogram 记录本次耗时

#### Scenario: OCR 错误计数

- **WHEN** OCR 处理抛出异常
- **THEN** `ocr_errors_total` Counter 增加 1