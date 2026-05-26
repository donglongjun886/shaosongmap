## Why

SSE 提取端点的 `event_stream()` 虽是 `async def`，但内部同步迭代 `run_extract_pipeline()` 生成器，LLM 调用 + 地理编码全程阻塞 asyncio 事件循环。单个提取请求期间整个服务无法处理任何其他请求（包括 `/health` 探针）。

## What Changes

- `routers/extract.py` 的 `event_stream()` 改为使用 `run_in_executor` 将同步管道卸载到线程池，通过 `asyncio.Queue` 桥接保持流式推送语义
- 管道执行期间事件循环不被阻塞，服务可持续响应健康检查和并发请求

## Capabilities

### Modified Capabilities
- `extraction-progress-streaming`: SSE 端点必须使用线程池执行同步管道，不得阻塞 asyncio 事件循环

## Impact

- `shaosongmap/routers/extract.py`：`event_stream()` 内部实现改为 Queue + run_in_executor 模式
- 不影响 API 契约、SSE 事件格式、前端消费逻辑