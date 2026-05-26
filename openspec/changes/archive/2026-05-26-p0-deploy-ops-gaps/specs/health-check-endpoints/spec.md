## ADDED Requirements

### Requirement: Liveness 探活端点 `/health`

系统 SHALL 提供 `/health` 端点，供 k8s liveness probe 使用。

该端点 MUST:
- 始终返回 HTTP 200 和 `{"status": "ok"}` 响应体
- 不依赖任何外部服务（无 DB 查询、无 API 调用）
- 在 10ms 内完成响应

#### Scenario: 正常探活

- **WHEN** GET 请求 `/health`
- **THEN** 返回 200 `{"status": "ok"}`

### Requirement: Readiness 就绪端点 `/ready`

系统 SHALL 提供 `/ready` 端点，供 k8s readiness probe 使用。

该端点 MUST:
- 检查 `app.state.settings` 中关键配置是否已加载（`deepseek_api_key` 非空）
- 检查 OCR 模型是否已初始化（`app.state.ocr_ready` 为 True）
- 全部就绪时返回 HTTP 200 `{"status": "ready"}`
- 任一条件不满足时返回 HTTP 503 `{"status": "not_ready", "reason": "..."}`

#### Scenario: 应用完全就绪

- **WHEN** 配置已加载且 OCR 模型已初始化
- **THEN** GET `/ready` 返回 200 `{"status": "ready"}`

#### Scenario: OCR 模型未就绪

- **WHEN** DeepSeek key 已配置但 OCR 模型尚未加载
- **THEN** GET `/ready` 返回 503，`reason` 字段说明未就绪原因

#### Scenario: 关键配置缺失

- **WHEN** `deepseek_api_key` 为空
- **THEN** GET `/ready` 返回 503，`reason` 字段指明缺失配置
