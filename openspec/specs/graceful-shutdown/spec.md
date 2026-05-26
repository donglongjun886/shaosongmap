# Graceful Shutdown 优雅关闭

## Purpose

定义应用关闭时的资源释放和请求排空行为，确保零停机部署。

## Requirements

### Requirement: 优雅关闭 — 模型资源释放

系统 SHALL 在应用关闭时释放 PaddleOCR 模型资源。

FastAPI lifespan SHALL:
- 在 `yield` 之后执行清理逻辑
- 调用 OCR 模型的资源释放方法（若存在）
- 记录日志：`正在关闭应用，释放资源...`

#### Scenario: SIGTERM 触发优雅关闭

- **WHEN** 应用收到 SIGTERM 信号
- **THEN** 系统在 30 秒内完成正在处理的请求，释放 OCR 模型，然后退出

#### Scenario: 关闭日志记录

- **WHEN** 应用开始关闭流程
- **THEN** 日志输出 `正在关闭应用，释放资源...`，结束后输出 `应用已关闭`

### Requirement: 优雅关闭 — 请求排空

系统 SHALL 在关闭信号后给进行中的请求足够时间完成。

uvicorn 配置 SHALL:
- 设置 `timeout_graceful_shutdown=30`（秒）
- 超时后强制终止未完成的请求

#### Scenario: 关闭时有进行中的请求

- **WHEN** 2 个 OCR 提取请求正在进行中，收到 SIGTERM
- **THEN** 系统等待请求完成（最长 30 秒），然后退出

#### Scenario: 请求超时强制终止

- **WHEN** OCR 请求耗时超过 30 秒且收到 SIGTERM
- **THEN** 系统在 30 秒后强制终止请求并退出