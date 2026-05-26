## Why

测试覆盖率在服务层严重不均衡（unit_banner 仅 14%、geo 60%、geojson 73%），可观测性仅覆盖核心 pipeline 模块（6 个模块无日志、无 trace ID 传递、无 metrics），安全加固缺少 CSP 响应头和 secrets 扫描。这是补齐工程规范审查（engineering_gap_analysis.md）P2/P3/P4 三个优先级缺口的一次性收尾。

## What Changes

- **测试补全**：为 `services/unit_banner.py`、`services/geo.py`、`services/geojson.py` 补齐单元测试，使服务层覆盖率全部 ≥80%
- **日志补全**：为 `routers/render.py`、`routers/extract.py`、`services/geo.py`、`services/geojson.py`、`services/unit_banner.py`、`geocoder.py` 添加结构化日志
- **Trace ID**：确保 extract → geocode → render 全链路传递 request_id，复用已有的 `_request_id_middleware`
- **Prometheus Metrics**：新增 `/metrics` 端点，暴露请求延迟、错误率、OCR 耗时等指标
- **CSP 响应头**：在 app.py 添加 Content-Security-Policy 中间件
- **Secrets 扫描**：在 `.pre-commit-config.yaml` 增加 detect-secrets hook，防止 `.env` 等敏感文件误提交

## Capabilities

### New Capabilities

- `service-test-coverage`: 为 services/ 层低覆盖率模块补齐单元测试，目标全部 ≥80%
- `observability-metrics`: 新增 Prometheus `/metrics` 端点，暴露请求延迟、错误率、OCR 耗时
- `security-headers`: 为 HTTP 响应添加 Content-Security-Policy 及其他安全响应头
- `secrets-scanning`: pre-commit 钩子增加 detect-secrets，扫描敏感信息泄露

### Modified Capabilities

- `structured-logging`: 将日志覆盖扩展到 routers/render、routers/extract、services/geo、services/geojson、services/unit_banner、geocoder 共 6 个模块，并在 pipeline 中传递 trace_id

## Impact

- 受影响代码：`services/unit_banner.py`、`services/geo.py`、`services/geojson.py`（测试补全）；`routers/render.py`、`routers/extract.py`、`services/geo.py`、`services/geojson.py`、`services/unit_banner.py`、`geocoder.py`、`services/pipeline.py`（日志 + trace ID）；`app.py`（CSP 中间件 + metrics 端点）
- 受影响配置：`.pre-commit-config.yaml`（新增 detect-secrets）、`pyproject.toml`（新增 prometheus-client 依赖）
- 新增依赖：`prometheus-client`、`detect-secrets`