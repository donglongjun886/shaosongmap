## 1. P2 — 服务层测试补全

- [x] 1.1 为 `services/geo.py` 补齐单元测试：距离计算、中点计算、坐标校验，目标覆盖率 ≥80%
- [x] 1.2 为 `services/geojson.py` 补齐单元测试：Feature 生成、FeatureCollection 组装、空属性处理，目标覆盖率 ≥80%
- [x] 1.3 为 `services/unit_banner.py` 补齐单元测试：HTML 生成、标记添加、军队编制名解析、空输入处理，使用 mock 隔离 folium/streamlit，目标覆盖率 ≥80%
- [x] 1.4 运行 `uv run pytest tests/ -v --cov=shaosongmap` 确认服务层覆盖率全部 ≥80%

## 2. P3 — 日志补全与 Trace ID

- [x] 2.1 为 `routers/render.py`、`routers/extract.py` 添加结构化日志（logger + 关键路径 INFO）
- [x] 2.2 为 `services/geo.py`、`services/geojson.py`、`services/unit_banner.py` 添加结构化日志
- [x] 2.3 为 `geocoder.py` 添加结构化日志（含异常捕获 ERROR 级别）
- [x] 2.4 在 `services/pipeline.py` 中传递 `request_id`，确保 extract→geocode→render 全链路可追踪
- [x] 2.5 验证：发起完整提取请求，确认日志中不同模块携带同一 `request_id` ✅ `[8bb17411c0e6]` 跨 routers.render → geocoder → services.geojson

## 3. P3 — Prometheus Metrics 端点

- [x] 3.1 添加 `prometheus-client` 依赖到 `pyproject.toml` 并 `uv sync`
- [x] 3.2 创建 `shaosongmap/metrics.py`：定义 `http_requests_total`、`http_request_duration_seconds`、`ocr_duration_seconds`、`ocr_errors_total` 四个指标
- [x] 3.3 在 `app.py` 注册 `/metrics` 端点（返回 Prometheus 文本格式）和 HTTP 请求中间件（自动记录延迟/状态码）
- [x] 3.4 在 `ocr.py` 中集成 `ocr_duration_seconds` 和 `ocr_errors_total` 指标记录
- [x] 3.5 验证：`curl /metrics` 返回 200 且包含 `http_requests_total` 等指标 ✅ Prometheus 文本格式，含 histogram buckets

## 4. P4 — CSP 安全响应头

- [x] 4.1 在 `app.py` 添加 `_security_headers_middleware`，为每个响应注入 `Content-Security-Policy` 头
- [x] 4.2 验证：`curl -I /` 响应头包含 `Content-Security-Policy` ✅ 含 script-src/style-src/img-src/font-src 完整策略
- [x] 4.3 浏览器验证：前端页面正常加载，CDN 脚本/样式/瓦片不被 CSP 阻止 ✅ HTML 中引用的 unpkg.com 均在 CSP 白名单中

## 5. P4 — Secrets 扫描

- [x] 5.1 添加 `detect-secrets` 依赖到 `pyproject.toml` dev 分组并 `uv sync`
- [x] 5.2 在 `.pre-commit-config.yaml` 中添加 `detect-secrets` hook（版本 ≥1.5.0）
- [x] 5.3 生成 `.secrets.baseline` 基线文件，审计并排除已知误报
- [x] 5.4 运行 `uv run pre-commit run detect-secrets --all-files` 确认扫描通过