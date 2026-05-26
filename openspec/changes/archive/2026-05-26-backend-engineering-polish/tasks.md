## 1. 配置层——启动校验

- [x] 1.1 安装 `pydantic-settings` 依赖，新建 `shaosongmap/config.py`，定义 `Settings(BaseSettings)` 模型，包含 `deepseek_api_key`、`deepseek_base_url`、`dashscope_api_key`、`cors_origins`、`log_level`、`log_format` 字段
- [x] 1.2 `app.py` 启动时实例化 `Settings()`，挂载到 `app.state.settings`，启动校验失败时输出明确错误信息并拒绝启动
- [x] 1.3 `shaosongmap/extractor.py` 和 `shaosongmap/geocoder.py` 改为从 `config.settings` 单例读取配置，移除函数内的 `os.getenv` 调用

## 2. 基础设施——日志、速率限制、CORS

- [x] 2.1 安装 `python-json-logger` 依赖，在 `app.py` 中实现 `RequestIDMiddleware`（注入/复用 `X-Request-ID`），配置 `logging.basicConfig` 支持 `LOG_FORMAT=text|json` 切换
- [x] 2.2 各模块 logger 升级为 `logging.getLogger(__name__)` 风格（替换硬编码的 `'shaosongmap'` 字符串），关键日志点补充 `extra={'request_id': ...}` 字段
- [x] 2.3 安装 `slowapi` 依赖，在 `app.py` 中挂载 `Limiter`，`/api/v1/extract` 限 5次/分，`/api/v1/ocr` 限 10次/分，`/api/v1/ocr/batch` 限 5次/分，返回统一错误格式
- [x] 2.4 `app.py` 中 CORS `allow_origins` 改为从 `settings.cors_origins` 读取，默认 `['*']`

## 3. 架构——Pipeline 归位 + 错误格式统一

- [x] 3.1 新建 `shaosongmap/services/pipeline.py`，将 `run_extract_pipeline` 函数和 `PipelineStage` dataclass 从 `routers/extract.py` 迁入，保持函数签名和逻辑不变
- [x] 3.2 `routers/extract.py` 中删除 `run_extract_pipeline` 和 `PipelineStage`，改为 `from shaosongmap.services.pipeline import run_extract_pipeline, PipelineStage`
- [x] 3.3 在 `schemas.py` 中新增 `ErrorResponse` 模型，统一定义 `{"error": {"code": str, "message": str, "detail": str}}` 结构
- [x] 3.4 `routers/ocr.py` 中所有 `raise HTTPException` 统一使用 `ErrorResponse` 格式的 detail

## 4. API 版本化——`/api/v1/` 前缀

- [x] 4.1 三个路由模块的 APIRouter 添加 `prefix='/api/v1'`（`routers/extract.py`、`routers/ocr.py`、`routers/render.py`）
- [x] 4.2 `app.py` 中 `include_router` 改为不重复声明 prefix（由各 router 自行携带）
- [x] 4.3 前端 `static/index.html` 中 API base URL 从 `/api/` 改为 `/api/v1/`

## 5. 文档收尾——requirements.txt + README

- [x] 5.1 清理 `requirements.txt`，移除 `pytest` 等开发依赖（保留在 `pyproject.toml` 的 `[dependency-groups].dev`），仅保留生产依赖
- [x] 5.2 更新 `README.md` 安装指南：`pip install -r requirements.txt` → `uv sync`，项目结构图反映 `routers/` + `services/` + `schemas/` 三层
- [x] 5.3 更新 `openspec/project.md` 项目结构图，反映分层架构 + 当前实际文件布局

## 6. 验证

- [x] 6.1 运行 `ruff format . && ruff check . --fix` 确保格式和 lint 通过
- [x] 6.2 运行 `mypy app.py shaosongmap/` 确保类型检查通过
- [x] 6.3 运行 `pytest tests/ -v --cov=shaosongmap` 确保所有 108 个测试通过且覆盖率不低于 77%（实际 78%）
- [x] 6.4 启动服务验证：`/docs`(200)、`/api/v1/extract`(200 SSE)、`/api/v1/render`(200)、`/api/v1/ocr`(422 缺文件)、`/api/v1/ocr/batch`(422 缺文件) 全部正常
- [x] 6.5 验证无 `DEEPSEEK_API_KEY` 时 `Settings()` 抛出 `ValidationError`，阻止启动
