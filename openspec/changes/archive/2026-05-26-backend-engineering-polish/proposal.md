## Why

分层架构重构后，后端在 API 设计规范、错误处理一致性、安全防护、可观测性、配置管理等方面存在多项不足。部分 spec 文档与代码实现不一致。本次变更系统性修复 10 项后端工程规范问题，提升项目的生产就绪度。

## What Changes

- **BREAKING** API 路径从 `/api/*` 迁移至 `/api/v1/*`
- **BREAKING** 提取管道编排函数从 `routers/extract.py` 移至 `services/pipeline.py`
- 统一所有端点的错误响应格式为 `{"error": {"code": "...", "message": "..."}}`
- CORS 允许域名改为环境变量可配，默认仍为 `*`
- 接入 `slowapi` 对 `/api/extract` 实施速率限制
- 引入 `pydantic-settings` 在应用启动时校验必需配置项
- 引入 request_id 中间件和结构化 JSON 日志
- 补充 `campaign-text-extraction` spec 缺失的 `camp` 地点类型
- 修正 `force-unit-visualization` spec 偏移算法描述与实际代码一致
- 清理过时的 `requirements.txt`，README 安装指南改为 uv

## Capabilities

### New Capabilities
- `api-error-response-standard`: 统一定义所有 API 端点的错误响应 JSON 结构
- `api-versioning`: API 路径版本化前缀 `/api/v1/`
- `api-rate-limiting`: 基于 slowapi 的请求速率限制，保护 LLM 调用端点
- `structured-logging`: 结构化 JSON 日志输出与 request_id 请求追踪
- `configuration-validation`: 启动时通过 pydantic-settings 校验必需配置项

### Modified Capabilities
- `layered-architecture`: 提取管道编排函数从 router 层移至 service 层
- `campaign-text-extraction`: PlaceType 枚举补充 `camp`（营寨）类型
- `force-unit-visualization`: 多部队偏移算法描述修正为"统一沿南北方向错位展开"
- `project-config`: CORS origins 环境变量可配；README 安装指令改用 uv

## Impact

- **路由文件**: `routers/extract.py`（移出 pipeline）、`routers/ocr.py`、`routers/render.py`（错误格式统一）
- **服务文件**: 新建 `services/pipeline.py`
- **入口文件**: `app.py`（CORS 配置、速率限制、request_id 中间件、JSON 日志、启动校验）
- **数据模型**: `schemas.py`（新增 ErrorResponse 模型）
- **新增依赖**: `slowapi`、`pydantic-settings`、`python-json-logger`
- **新增文件**: `shaosongmap/config.py`
- **规范文件**: 4 个现有 spec 的增量更新
- **文档**: `requirements.txt`、`README.md` 安装指南