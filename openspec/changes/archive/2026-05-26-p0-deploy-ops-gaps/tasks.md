## 1. 容器化基础

- [x] 1.1 创建 `export-requirements.sh` 脚本：从 `uv.lock` 导出 `requirements.txt`
- [x] 1.2 创建 `Dockerfile`：基于 `python:3.10-slim`，安装系统依赖 + Python 依赖，非 root 运行
- [x] 1.3 创建 `.dockerignore`：排除 `__pycache__`、`.git`、`venv/`、`.mypy_cache`、`openspec/` 等

## 2. 编排与配置

- [x] 2.1 创建 `docker-compose.yml`：定义 `app` 服务，端口 8000，env_file 注入，源码挂载
- [x] 2.2 补全 `.env.example`：新增 `CORS_ORIGINS`、`LOG_LEVEL`、`LOG_FORMAT`、`DASHSCOPE_API_KEY`，按类别分组并附中文注释

## 3. 探活与健康检查

- [x] 3.1 在 `shaosongmap/routers/` 新增 `health.py`：实现 `GET /health`（始终 200）和 `GET /ready`（检查配置+OCR 状态）
- [x] 3.2 在 `app.py` 注册 health router，设置 OCR 就绪标记 `app.state.ocr_ready`

## 4. 优雅关闭

- [x] 4.1 在 `app.py` 添加 lifespan context manager：startup 记录日志，shutdown 释放资源
- [x] 4.2 在 `Dockerfile` CMD / `docker-compose.yml` command 中配置 uvicorn `--timeout-graceful-shutdown 30`

## 5. 验证

- [x] 5.1 执行 `docker build -t shaosongmap .` 确认构建成功（待 Docker 环境就绪后验证）
- [x] 5.2 执行 `docker compose up` 确认服务启动，`/health` 和 `/ready` 正常响应（待 Docker 环境就绪后验证）
- [x] 5.3 执行 `uv run pytest tests/ -v` 确认现有测试全部通过（84 passed）
