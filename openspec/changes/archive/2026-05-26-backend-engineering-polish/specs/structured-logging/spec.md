## ADDED Requirements

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

#### Scenario: 请求自动获得 request_id

- **WHEN** 客户端发起一个未携带 `X-Request-ID` header 的请求
- **THEN** 响应头 `X-Request-ID` 包含生成的 UUID，所有日志记录携带此 ID

#### Scenario: 上游传入 request_id 被复用

- **WHEN** 客户端在请求头中携带 `X-Request-ID: abc-123`
- **THEN** 系统复用此 ID，响应头 `X-Request-ID` 仍为 `abc-123`，日志记录携带 `abc-123`
