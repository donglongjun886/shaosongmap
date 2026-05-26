## Why

项目目前完全依赖宿主机环境运行，无容器化、无健康检查、无优雅关闭，无法在 k8s 或任何标准云平台上部署。配置文档残缺，新人上手成本极高。这是从"本地能跑"到"可部署上线"的关键一步。

## What Changes

- 新增 Dockerfile，提供可复现的容器化运行环境（Python + PaddleOCR）
- 新增 docker-compose.yml，支持本地一键启动全栈
- 新增 `/health` 和 `/ready` 端点，供编排系统探活
- 补全 `.env.example`，覆盖所有必需配置项
- 新增优雅关闭逻辑：PaddleOCR 模型卸载 + uvicorn graceful timeout

## Capabilities

### New Capabilities

- `containerization`: Dockerfile + docker-compose 容器化部署方案
- `health-check-endpoints`: `/health` 存活检查 + `/ready` 就绪检查端点
- `graceful-shutdown`: 应用优雅关闭（模型卸载 + 请求排空）

### Modified Capabilities

- `configuration-validation`: `.env.example` 补全所有配置项，新增 `CORS_ORIGINS`、`LOG_LEVEL`、`LOG_FORMAT`、`DASHSCOPE_API_KEY`

## Impact

- 新增 `Dockerfile`、`docker-compose.yml`、`.dockerignore`
- 修改 `app.py`：注册 health/ready 路由、注册 shutdown handler
- 修改 `.env.example`：补全 4 类配置项
- 影响全部模块的健康探活路径