## ADDED Requirements

### Requirement: 统一 API 错误响应格式

所有非 SSE 端点的错误响应 SHALL 遵循统一 JSON 结构：

```json
{"error": {"code": "ERROR_CODE", "message": "中文简述", "detail": "..."}}
```

- `code` MUST 为大写下划线格式的错误码（如 `INVALID_INPUT`、`NOT_FOUND`）
- `message` MUST 为面向用户的中文简述
- `detail` MAY 包含技术细节（如具体字段名、原始异常信息）

SSE 流式端点（`/api/v1/extract`、`/api/v1/ocr/batch`）SHALL 保持现有 `error` 事件格式不变。

#### Scenario: OCR 端点格式校验失败

- **WHEN** 上传的文件 content-type 不是 `image/png` 或 `image/jpeg`
- **THEN** 返回 HTTP 400，响应体为 `{"error": {"code": "UNSUPPORTED_MEDIA", "message": "仅支持 PNG 和 JPEG 格式"}}`

#### Scenario: Extract 端点输入为空

- **WHEN** 提交的 `text` 字段为空或仅含空白字符
- **THEN** 返回 HTTP 422，响应体为 `{"error": {"code": "INVALID_INPUT", "message": "战役文本不能为空"}}`

#### Scenario: SSE 流式端点错误保持现有格式

- **WHEN** `/api/v1/extract` 的 SSE 管道中 extract 阶段失败
- **THEN** 发送 `event: error` 事件，data 为 `{"stage": "extract", "message": "..."}`

#### Scenario: 未知异常统一兜底

- **WHEN** 服务端发生未预期的内部错误
- **THEN** 返回 HTTP 500，响应体为 `{"error": {"code": "INTERNAL_ERROR", "message": "服务器内部错误", "detail": "..."}}`，detail SHALL 不包含敏感信息