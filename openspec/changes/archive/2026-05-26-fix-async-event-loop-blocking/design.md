## Context

`run_extract_pipeline()` 是同步 generator，内部执行 LLM API 调用和地理编码（可耗时 5-30 秒）。当前 `routers/extract.py` 的 `event_stream()` 虽是 `async def`，但 `for stage in run_extract_pipeline(...)` 同步迭代时没有任何 `await` 点，全程阻塞事件循环。

FastAPI/Starlette 默认线程池很小（`concurrent.futures.ThreadPoolExecutor`，默认 `min(32, os.cpu_count() + 4)`），但对这个场景足够——管道的瓶颈是 I/O（HTTP 调用），而非 CPU。

## Goals / Non-Goals

**Goals:**
- 提取管道执行期间 asyncio 事件循环不被阻塞
- `/health` 探针和其他端点保持可响应
- 保持 SSE 流式推送语义（阶段进度实时推送，不等到全部完成）

**Non-Goals:**
- 不改造管道内部为 async（改造成本高，涉及 openai 客户端异步化）
- 不引入额外依赖（仅用 stdlib `asyncio` + `concurrent.futures`）
- 不改变 API 契约和 SSE 事件格式

## Decisions

### 方案：`asyncio.Queue` + `run_in_executor`

在 `event_stream()` 内部创建 `asyncio.Queue`，将 `run_extract_pipeline()` 通过 `loop.run_in_executor()` 提交到默认线程池。线程内迭代同步 generator，将每个 `PipelineStage` 放入 queue。async 侧从 queue 读取并 yield SSE 事件。

```
┌─────────────────────────────────────┐
│         event_stream()              │
│                                     │
│  ┌──────────┐     ┌──────────────┐ │
│  │ Thread   │     │ Async Loop   │ │
│  │ Pool     │────▶│ (main)       │ │
│  │          │ put │              │ │
│  │ pipeline │     │ queue.get()  │ │
│  │ yield    │     │ yield sse    │ │
│  └──────────┘     └──────────────┘ │
└─────────────────────────────────────┘
```

**替代方案 A：收集全部 stage 再 yield**
- 更简单，但失去流式推送——用户要等到全部完成后才看到进度
- 不采用，流式体验是核心特性

**替代方案 B：改造管道为 async**
- 需要把 openai 客户端换成 async 版本，geocoder 也改 async
- 改动面大，风险高，当前性价比低
- 不采用

### Sentinel 模式

管道结束后，线程放入一个 `None` 作为 sentinel，async 侧读到 `None` 时停止迭代。

## Risks / Trade-offs

- [线程安全] `PipelineStage` 对象在子线程创建、主线程消费 → 字段均为不可变基本类型，无竞争条件
- [Queue 满] 默认无界，管道 stage 数量 ≤10，不会内存问题
- [异常传播] 线程内异常通过 queue 传递 `(False, exception)` 元组，async 侧 re-raise