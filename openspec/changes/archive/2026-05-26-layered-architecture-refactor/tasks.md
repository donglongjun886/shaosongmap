## 1. 目录创建

- [x] 1.1 创建 `shaosongmap/routers/` 和 `shaosongmap/services/` 目录及 `__init__.py`

## 2. Schemas 层迁出

- [x] 2.1 创建 `shaosongmap/schemas.py`，将 `app.py` 中 4 个 Pydantic 模型（`ExtractRequest`、`ExtractResponse`、`RenderRequest`、`OcrResponse`）迁入
- [x] 2.2 更新 `app.py` 中的 schemas 导入（`from shaosongmap.schemas import ...`）

## 3. Services 层迁出

- [x] 3.1 创建 `shaosongmap/services/geo.py`：迁入 `_DIRECTION_ANGLE`、`_angle_for_direction`、`_compute_data_diagonal`、`_offset_point`、`_DYNASTY_YEARS`
- [x] 3.2 创建 `shaosongmap/services/geojson.py`：迁入 `_compute_step_map`、`_make_geojson`、`_build_routes`
- [x] 3.3 创建 `shaosongmap/services/unit_banner.py`：迁入 `_make_unit_banner_features`、`_compute_unit_offsets`、`_make_unit_geojson`
- [x] 3.4 更新 `app.py` 中的 services 导入

## 4. Routers 层迁出

- [x] 4.1 创建 `shaosongmap/routers/ocr.py`：迁入 `/api/ocr` 和 `/api/ocr/batch` 端点，含 `_ALLOWED_IMAGE_TYPES` 和 `_MAX_IMAGE_SIZE` 常量
- [x] 4.2 创建 `shaosongmap/routers/render.py`：迁入 `/api/render` 端点
- [x] 4.3 创建 `shaosongmap/routers/extract.py`：迁入 `/api/extract` 端点，定义 `PipelineStage` dataclass，实现 SSE 分层（服务 generator → 路由 SSE 序列化）
- [x] 4.4 创建 `shaosongmap/utils.py`：迁入 `_sse_event` 工具函数

## 5. app.py 精简 + 死代码清理

- [x] 5.1 删除 `_run_pipeline` 函数
- [x] 5.2 精简 `app.py`：保留 FastAPI 实例化、CORS 中间件、lifespan、路由注册、静态文件挂载
- [x] 5.3 更新 `app.py` 所有导入为从新模块导入

## 6. 验证

- [x] 6.1 运行 `ruff check .` 确认零违规
- [x] 6.2 运行 `mypy app.py shaosongmap/` 确认类型检查通过
- [x] 6.3 运行 `PYTHONPATH=. pytest tests/ -v --cov=shaosongmap` 确认 108 测试全部通过
- [x] 6.4 运行 `pre-commit run --all-files` 确认四钩子全绿
