# API Versioning API 版本化

## Purpose

定义 API 路径版本化策略，确保向后兼容性和平滑迁移。

## Requirements

### Requirement: API 路径版本化

所有 API 端点 SHALL 使用 `/api/v1/` 路径前缀，与现有 `/api/` 前缀形成区分。

现有端点迁移映射：

| 旧路径 | 新路径 |
|--------|--------|
| `/api/ocr` | `/api/v1/ocr` |
| `/api/ocr/batch` | `/api/v1/ocr/batch` |
| `/api/extract` | `/api/v1/extract` |
| `/api/render` | `/api/v1/render` |

前端静态文件挂载（`/`）SHALL 不受影响。

#### Scenario: 新版本路径访问正常

- **WHEN** 客户端向 `/api/v1/extract` 发送 POST 请求
- **THEN** 后端正常处理，行为与旧 `/api/extract` 完全一致

#### Scenario: 旧路径不再可用

- **WHEN** 客户端向 `/api/extract` 发送 POST 请求
- **THEN** 返回 HTTP 404 Not Found

#### Scenario: Swagger 文档反映版本化

- **WHEN** 开发者访问 `/docs` Swagger UI
- **THEN** 所有端点的路径均显示 `/api/v1/` 前缀