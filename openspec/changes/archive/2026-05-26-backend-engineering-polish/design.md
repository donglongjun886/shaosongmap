## Context

分层架构重构（`a3feb44`）将 829 行 `app.py` 拆分为 `routers/` + `services/` + `schemas/` 三层。重构后审查发现 10 项后端工程规范问题，涉及 API 设计、安全防护、可观测性、配置管理和规范文档一致性。

当前状态：
- FastAPI 应用入口 `app.py` 52 行，CORS 硬编码 `allow_origins=['*']`
- 三个路由模块各自采用不同的错误处理模式
- `run_extract_pipeline`（150 行）位于 `routers/extract.py`，违反分层架构 spec
- 配置通过 `os.getenv` + `load_dotenv` 在函数内按需读取
- 日志使用标准 `logging` 模块，无结构化输出和请求追踪
- 现有 `requirements.txt` 与 `pyproject.toml` 的依赖声明不同步

## Goals / Non-Goals

**Goals:**
- 统一 API 错误响应格式，降低前端处理复杂度
- 管道编排逻辑归位到 services 层，消除 spec 与代码的不一致
- 引入速率限制保护 LLM 调用端点的费用安全
- 启动时校验配置完整性，避免运行时才发现配置缺失
- 结构化日志 + request_id 追踪，提升问题排查效率
- API 路径版本化，为未来接口演进预留空间
- 修正 4 个现有 spec 的文档错误或遗漏

**Non-Goals:**
- 不引入新的测试用例（另有独立变更处理）
- 不修改前端代码（除 base URL 一处）
- 不引入数据库或缓存层
- 不改变现有 API 的语义或业务行为
- 不添加 Docker 容器化（另有独立变更处理）

## Decisions

### 1. Pipeline 移动策略

**决策**: 新建 `services/pipeline.py`，将 `run_extract_pipeline` 及其 `PipelineStage` dataclass 整体迁移。router 层仅保留 SSE 序列化和 `StreamingResponse` 返回。

**理由**: 与 `layered-architecture` spec 保持一致，且 pipeline 可直接 import 测试而无需启动 FastAPI TestClient。

**替代方案**: 修改 spec 允许 router 层包含管道编排 → 拒绝。这会模糊分层边界，且 spec 已明确定义此约束。

### 2. 错误响应格式

**决策**: 统一采用 FastAPI 原生 `HTTPException` + Pydantic `ErrorResponse` 模型。

```json
{"error": {"code": "INVALID_INPUT", "message": "数据格式错误", "detail": "..."}}
```

非 SSE 端点在路由层 `raise HTTPException`，由 FastAPI 默认异常处理器序列化。SSE 端点保留现有 `error` 事件格式。

**理由**: 沿用 FastAPI 惯用模式，最小化前端改动。不引入全局异常处理器，保持简单。

**替代方案**: 全局 `exception_handler` 拦截所有异常 → 拒绝。过度设计，且 SSE 流式端点不受异常处理器控制。

### 3. 速率限制方案

**决策**: 使用 `slowapi`（基于 `limits` 库），通过 `app.state` 挂载 `Limiter`。

- `/api/v1/extract`：每 IP 每分钟 5 次
- `/api/v1/ocr`：每 IP 每分钟 10 次

使用 `X-Real-IP` 或 `X-Forwarded-For` header 识别客户端 IP。

**理由**: `slowapi` 是 FastAPI 生态的成熟方案，内存存储、零外部依赖。分钟级窗口对 LLM API 调用场景足够。

**替代方案**: nginx/API Gateway 层限流 → 拒绝。增加部署复杂度，且本地开发环境不受保护。

### 4. 配置校验方案

**决策**: 引入 `pydantic-settings`，新建 `shaosongmap/config.py`。

```python
class Settings(BaseSettings):
    deepseek_api_key: str
    deepseek_base_url: str = "https://api.deepseek.com"
    dashscope_api_key: str = ""
    cors_origins: list[str] = ["*"]
    log_level: str = "INFO"
```

`app.py` 启动时读取一次 `Settings()`，各模块从 `config.py` import 单例。

**理由**: 启动时即发现缺失配置，而非运行时在 `extractor.py:44` 抛 `ValueError`。类型安全，有默认值，IDE 有补全。

**替代方案**: 手写 `_validate_config()` 函数 → 拒绝。重复造轮子，pydantic-settings 已是业界标准。

### 5. 结构化日志方案

**决策**: 使用 `python-json-logger` + 自定义 `log_config` dict 配置。

```python
# 日志格式
{"timestamp": "2026-05-26T10:30:00", "level": "INFO", "logger": "shaosongmap.routers.extract",
 "request_id": "a1b2c3d4", "message": "Stage 1 提取完成", "elapsed_ms": 1230}
```

通过 Starlette middleware 注入 `X-Request-ID`（nuuid），并存入 `logging.LogRecord` 的 extra 字段。

**理由**: JSON 格式方便接入 ELK/Loki 等日志平台。request_id 是分布式追踪最小原语，未来可平滑升级到 OpenTelemetry。

### 6. API 版本化策略

**决策**: 所有现有端点从 `/api/*` 迁移至 `/api/v1/*`。在 `app.py` 中通过 `router.prefix` 统一添加版本前缀。

**影响**: 前端需要一处修改（base URL）。这是唯一的 **BREAKING** 变更。

**理由**: URL 路径版本化是 REST API 的事实标准，比 header 版本化更直观、更易调试。

**替代方案**: Header-based versioning (`Accept: application/vnd.shaosongmap.v1+json`) → 拒绝。对浏览器端不友好，调试困难。

## Risks / Trade-offs

- **[BREAKING] 前端 base URL 变更** → 单文件 HTML 中仅一处硬编码，改动前后端联动部署即可。风险低。
- **slowapi 内存存储** → 多进程/多实例部署时各自独立计数。后续可切换到 Redis backend，当前单实例部署无影响。
- **pydantic-settings 引入新依赖** → 轻量依赖，与现有 Pydantic 生态兼容，无冲突风险。
- **JSON 日志 vs 控制台可读性** → 开发环境保持标准文本格式，仅生产环境启用 JSON 输出。通过 `LOG_FORMAT` 环境变量切换。

## Migration Plan

1. 所有变更在单次提交中完成，作为不可拆分的原子变更
2. 部署前后端需同步更新：
   - 后端：`/api/*` → `/api/v1/*`
   - 前端：修改 `static/index.html` 中 base URL
3. 无数据库迁移，无状态变更
4. 回滚策略：git revert 单次提交

## Open Questions

- （无）所有设计决策已有明确结论
