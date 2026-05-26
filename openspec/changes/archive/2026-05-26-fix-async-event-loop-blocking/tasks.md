## 1. 核心实现

- [x] 1.1 `routers/extract.py` 的 `event_stream()` 改为 `asyncio.Queue` + `run_in_executor` 模式
- [x] 1.2 添加 `import asyncio` 到 extract.py 导入区

## 2. 验证

- [x] 2.1 运行 `PYTHONPATH=. uv run pytest tests/ -v --cov=shaosongmap` 确认无回归
- [x] 2.2 启动服务 `uv run python app.py`，发起提取请求期间 `curl /health` 确认不被阻塞
