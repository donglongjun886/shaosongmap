# API Rate Limiting 请求速率限制

## Purpose

定义对 LLM 调用端点的请求速率限制策略，防止滥用并确保服务可用性。

## Requirements

### Requirement: 基于 IP 的请求速率限制

系统 SHALL 对以下 LLM 调用端点实施基于客户端 IP 的速率限制：

| 端点 | 限制 | 窗口 |
|------|------|------|
| `/api/v1/extract` | 5 次 | 每分钟 |
| `/api/v1/ocr` | 10 次 | 每分钟 |
| `/api/v1/ocr/batch` | 5 次 | 每分钟 |

客户端 IP MUST 优先从 `X-Forwarded-For` header 获取（反向代理部署），回退到 `X-Real-IP` header，最终回退到直接连接 IP。

超限时 SHALL 返回 HTTP 429 Too Many Requests，响应体符合统一错误格式。

#### Scenario: 正常请求不受影响

- **WHEN** 客户端在 1 分钟内第 3 次调用 `/api/v1/extract`
- **THEN** 请求正常处理，响应头包含 `X-RateLimit-Remaining: 2`

#### Scenario: 超出限制返回 429

- **WHEN** 客户端在 1 分钟内第 6 次调用 `/api/v1/extract`
- **THEN** 返回 HTTP 429，响应体为 `{"error": {"code": "RATE_LIMITED", "message": "请求过于频繁，请稍后再试"}}`

#### Scenario: Rate limit 按 IP 独立计数

- **WHEN** 客户端 A 在第 6 次请求被限制后，客户端 B 发起首次请求
- **THEN** 客户端 B 的请求正常处理，两个 IP 的计数器互不影响

#### Scenario: Render 端点不受限制

- **WHEN** 客户端频繁调用 `/api/v1/render`（不调用 LLM API）
- **THEN** 请求不受速率限制影响，正常处理