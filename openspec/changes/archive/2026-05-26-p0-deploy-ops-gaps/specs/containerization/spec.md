## ADDED Requirements

### Requirement: Docker 镜像构建

项目 MUST 提供 `Dockerfile`，使任何人可在标准 Docker 环境中构建并运行应用。

Dockerfile SHALL:
- 基于 `python:3.10-slim` 镜像
- 安装 PaddleOCR 所需的系统依赖（libgomp1、libglib2.0-0 等）
- 复制源码并安装 Python 依赖
- 以非 root 用户运行应用
- 通过 `EXPOSE 8000` 声明端口
- 使用 `CMD` 启动 uvicorn

#### Scenario: 成功构建镜像

- **WHEN** 用户在项目根目录执行 `docker build -t shaosongmap .`
- **THEN** 镜像构建成功，`docker images` 可见 `shaosongmap` 镜像

#### Scenario: 成功启动容器

- **WHEN** 用户执行 `docker run -p 8000:8000 --env-file .env shaosongmap`
- **THEN** 访问 `http://localhost:8000` 返回正常响应

### Requirement: docker-compose 一键启动

项目 MUST 提供 `docker-compose.yml`，支持 `docker compose up` 一键启动应用。

compose 文件 SHALL:
- 定义 `app` 服务，映射宿主机 8000 端口
- 从 `.env` 文件注入环境变量
- bind mount 源码目录以支持开发热重载（dev profile）
- 包含 `.dockerignore` 排除 `__pycache__`、`.git`、`venv/`、`.mypy_cache` 等目录

#### Scenario: compose 启动成功

- **WHEN** 用户执行 `docker compose up`
- **THEN** 服务在 `http://localhost:8000` 可用

#### Scenario: .dockerignore 排除无关文件

- **WHEN** 构建镜像
- **THEN** `__pycache__`、`.git`、`venv/` 等目录不在镜像内
