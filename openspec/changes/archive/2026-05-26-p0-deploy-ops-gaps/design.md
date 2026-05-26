## Context

当前项目仅能在开发者宿主机上运行，依赖手动安装的 Python 3.10+、PaddleOCR 及其系统库。无容器化方案，无法部署到 k8s 或任何标准云平台。`.env.example` 仅含 2 个变量，新贡献者难以正确配置环境。应用无探活端点、无优雅关闭，不适合生产运行。

## Goals / Non-Goals

**Goals:**
- 提供 Dockerfile，使任何人 `docker build` 即可获得一致的运行环境
- 提供 docker-compose.yml，本地 `docker compose up` 一键启动
- 新增 `/health` 和 `/ready` 端点，支持 k8s liveness/readiness probe
- 补全 `.env.example`，覆盖所有配置项并附带注释说明
- 注册 FastAPI 生命周期钩子，实现 PaddleOCR 模型卸载和请求排空

**Non-Goals:**
- 不引入 Kubernetes manifests / Helm chart（未来单独做）
- 不引入 CI 部署流水线（属于 P5 范畴）
- 不做多阶段构建优化（镜像尺寸在此阶段非首要矛盾）
- 不添加 PostgreSQL 数据库容器（数据层尚未落地）

## Decisions

### 1. 基础镜像：`python:3.10-slim`

**选型理由**: 项目目标 Python 3.10+，slim 镜像在体积和兼容性间取得平衡。PaddleOCR 需要的系统库（libgomp1、libglib2.0-0、libgomp1 等）在 slim 上均可通过 apt 安装。

**替代方案**: `python:3.10`（完整 Debian，镜像更大但省去 apt 调试）— 不选，slim 体积小约 40%。

### 2. 依赖安装：直接 `pip install` 而非 uv sync

**选型理由**: Docker 构建环境不需要 uv 的锁文件功能。直接 `pip install` 减少构建层数和复杂度。`uv.lock` 仍为本地开发保留。`requirements.txt` 从 `uv.lock` 导出以确保一致性。

### 3. 健康检查拆分为 `/health`（liveness）和 `/ready`（readiness）

**选型理由**: k8s 标准实践。liveness probe 应极轻量（仅确认进程存活），readiness probe 检查外部依赖（DashScope API key 配置、OCR 模型加载）。两者分开可避免探活失败导致不必要的 Pod 重启。

**实现**: `/health` 返回 `{"status": "ok"}` 200。`/ready` 检查 `app.state.settings` 和 OCR 模型状态，失败返回 503。

### 4. 优雅关闭：FastAPI lifespan + uvicorn timeout

**选型理由**: FastAPI 的 lifespan context manager 是官方推荐的资源管理方式。uvicorn 配置 `timeout_graceful_shutdown` 控制请求排空窗口。

**实现**:
- lifespan 的 `yield` 之后执行清理：释放 PaddleOCR 模型、关闭连接池
- uvicorn 启动参数加 `--timeout-graceful-shutdown 10`
- 信号处理由 uvicorn 内置，无需自建 signal handler

### 5. `.env.example` 结构

按类别分组，每项附带简短中文注释和默认值。新增 `CORS_ORIGINS`、`LOG_LEVEL`、`LOG_FORMAT`、`DASHSCOPE_API_KEY`。

## Risks / Trade-offs

- [PaddleOCR 镜像体积] 模型包约 200MB+，首次 `docker pull` 较慢 → 使用 `.dockerignore` 排除无关文件，考虑后续用模型挂载卷拆分
- [热重载] docker-compose 默认 bind mount 源码目录 + uvicorn `--reload`，适合开发但不适合生产 → compose 文件通过 profile 区分 dev/prod 模式
- [uvicorn timeout] `timeout_graceful_shutdown` 默认 30s，PaddleOCR 推理可能超时 → 设为 30s，足够覆盖单次 OCR 调用
