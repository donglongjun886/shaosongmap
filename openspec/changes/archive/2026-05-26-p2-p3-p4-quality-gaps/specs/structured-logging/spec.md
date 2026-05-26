# Structured Logging 结构化日志 (Delta)

## MODIFIED Requirements

### Requirement: 结构化 JSON 日志输出

系统 SHALL 支持通过 `LOG_FORMAT` 环境变量切换日志输出格式：

- `LOG_FORMAT=text`（默认）：标准文本格式，适合开发环境
- `LOG_FORMAT=json`：JSON 格式，每行一条 JSON 记录

每行日志记录 MUST 包含以下字段：
- `timestamp`：ISO 8601 格式时间戳
- `level`：日志级别（DEBUG / INFO / WARNING / ERROR）
- `logger`：logger 名称（如 `shaosongmap.routers.extract`）
- `request_id`：请求唯一标识（如有）
- `message`：日志消息

日志覆盖范围 SHALL 扩展至以下模块：
- 所有 `routers/` 模块（extract、ocr、render、health）
- 所有 `services/` 模块（pipeline、geo、geojson、unit_banner）
- 顶层业务模块（extractor、geocoder、ocr）

#### Scenario: 开发环境使用文本格式

- **WHEN** 未设置 `LOG_FORMAT` 或设置为 `text`
- **THEN** 日志输出为人类可读格式：`2026-05-26 10:30:00 INFO shaosongmap.routers.extract [a1b2c3d4] Stage 1 提取完成`

#### Scenario: 生产环境使用 JSON 格式

- **WHEN** `LOG_FORMAT=json`
- **THEN** 日志输出为 JSON Lines 格式，可被 ELK/Loki 直接解析

### Requirement: Request ID 追踪

系统 SHALL 通过 Starlette middleware 为每个 HTTP 请求注入唯一标识符。

请求进入时 MUST：
1. 检查 `X-Request-ID` 请求头，如有则复用（支持上游传入）
2. 如无则生成 UUID7（时间排序友好）
3. 存入 `logging.LogRecord` 的 extra 字段
4. 在响应头 `X-Request-ID` 中返回给客户端

服务层 SHALL 通过 `contextvars` 传递 `request_id`，确保 middleware 之外的调用链（如 extract → geocode → render）也能在日志中携带同一 `request_id`。

#### Scenario: 请求自动获得 request_id

- **WHEN** 客户端发起一个未携带 `X-Request-ID` header 的请求
- **THEN** 响应头 `X-Request-ID` 包含生成的 UUID，所有日志记录携带此 ID

#### Scenario: 上游传入 request_id 被复用

- **WHEN** 客户端在请求头中携带 `X-Request-ID: abc-123`
- **THEN** 系统复用此 ID，响应头 `X-Request-ID` 仍为 `abc-123`，日志记录携带 `abc-123`

#### Scenario: 服务层日志携带 request_id

- **WHEN** `services/pipeline.py` 的 `run_pipeline()` 被调用
- **THEN** 其日志记录 SHALL 携带与当前 HTTP 请求相同的 `request_id`

## ADDED Requirements

### Requirement: 全模块日志覆盖

系统 SHALL 确保以下模块具备独立的 `logging.getLogger(__name__)` 实例：

- `shaosongmap.routers.render`
- `shaosongmap.routers.extract`
- `shaosongmap.services.geo`
- `shaosongmap.services.geojson`
- `shaosongmap.services.unit_banner`
- `shaosongmap.geocoder`

每个模块 MUST 在关键路径记录 INFO 级别日志：
- 函数入口（含关键参数摘要）
- 函数出口（含结果摘要）
- 异常捕获点（WARNING 或 ERROR 级别）

#### Scenario: render 路由日志记录

- **WHEN** 客户端请求 `/api/v1/render`
- **THEN** `shaosongmap.routers.render` logger 记录 INFO 日志，包含图层类型和要素数量

#### Scenario: geocoder 异常日志

- **WHEN** `geocoder.py` 的地理编码查询抛出异常
- **THEN** `shaosongmap.geocoder` logger 记录 ERROR 日志，包含异常类型和输入参数