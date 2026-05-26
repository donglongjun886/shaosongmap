## Context

当前项目测试总体覆盖率为 78%，但服务层三个模块严重偏低：`unit_banner.py`（14%）、`geo.py`（60%）、`geojson.py`（73%）。可观测性方面，结构化日志已在核心 pipeline 模块引入，但 6 个模块仍无日志；`app.py` 已有 `_request_id_middleware` 但未在服务层传递。安全加固方面，P1 已补上 CDN SRI，剩余 CSP 响应头和 secrets 扫描两项。

本次变更在已有架构上增量补齐，不引入新的架构模式，无需数据库变更。

## Goals / Non-Goals

**Goals:**
- `services/` 层全部模块测试覆盖率 ≥80%
- 所有业务模块（routers/services/geocoder）具备结构化日志
- extract → geocode → render 全链路可追踪（request_id）
- 提供 Prometheus `/metrics` 端点，暴露请求延迟、错误率、OCR 耗时
- HTTP 响应包含 Content-Security-Policy 安全头
- pre-commit 包含 detect-secrets 扫描

**Non-Goals:**
- 不做分布式 tracing（Jaeger/Zipkin），request_id 传递足够
- 不设 Grafana 仪表板或告警规则
- 不做 CSP 报告收集（report-uri/report-to）
- 不做 P5（CI/CD 增强）和 P6（数据层持久化）

## Decisions

### D1: 测试策略 — 按模块特征选择 Mock 策略

- `geo.py`：纯计算逻辑（距离/中点），直接单元测试，无需 mock
- `geojson.py`：GeoJSON 序列化，测试输入输出映射，无需 mock
- `unit_banner.py`：依赖 `streamlit` 和 `folium`，需要 mock folium 对象和 Streamlit session state

**理由**：前两者是纯函数，直接测试成本低；unit_banner 依赖外部 UI 框架，mock 是最小成本的可行方案。

### D2: Prometheus 客户端选型 — prometheus_client

选用官方 `prometheus-client` 库，FastAPI 生态有成熟集成模式。指标设计：

- `http_requests_total{method, endpoint, status}` — Counter
- `http_request_duration_seconds{method, endpoint}` — Histogram
- `ocr_duration_seconds` — Histogram
- `ocr_errors_total` — Counter
- `extraction_duration_seconds` — Histogram

端点挂载在 `/metrics`，无需鉴权（内网场景）。

### D3: 日志注入方式 — 依赖注入 request_id

不改造每个函数签名。利用 Python `logging.LogRecord` 的 `extra` 字段 + contextvars 在 middleware 层注入 request_id，各模块通过 `logging.getLogger(__name__)` 自动获取。与已有的 `_request_id_middleware` 完全兼容。

### D4: CSP 策略 — 宽松起步

考虑到前端使用 Leaflet CDN、内联样式和 blob URL（截图下载），CSP 策略不能太激进：

```
default-src 'self';
script-src 'self' https://cdn.jsdelivr.net https://unpkg.com;
style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://unpkg.com;
img-src 'self' data: blob: https://*.tile.openstreetmap.org;
connect-src 'self';
font-src 'self' https://cdn.jsdelivr.net;
```

**替代方案考虑**：strict-dynamic + nonce 方案更安全，但需要改造前端所有内联样式，工程量过大，暂不采用。

### D5: Secrets 扫描 — detect-secrets

选用 Yelp 的 `detect-secrets`（而非 gitleaks），原因：
- Python 原生，与现有技术栈一致
- 支持基线文件（`.secrets.baseline`），已有误报可审计后排除
- pre-commit 集成成熟

## Risks / Trade-offs

- [Risk] `unit_banner.py` 的 folium/streamlit mock 可能不覆盖实际渲染行为 → **Mitigation**：仅测试数据转换逻辑，不测试地图渲染
- [Risk] CSP 策略过宽，安全收益有限 → **Mitigation**：明确标注当前为"起步策略"，后续收紧需前端配合
- [Risk] Prometheus metrics 端点无鉴权，公网暴露有信息泄露风险 → **Mitigation**：文档注明仅内网使用，或后续加 middlewares 白名单

## Open Questions

- 无
