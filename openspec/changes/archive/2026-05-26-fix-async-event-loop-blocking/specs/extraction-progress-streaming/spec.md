## ADDED Requirements

### Requirement: SSE 端点不阻塞事件循环

系统 SHALL 在 SSE 提取端点中将同步管道的执行卸载到线程池（`run_in_executor`），确保 asyncio 事件循环在管道执行期间不被阻塞。

实现 MUST：
- 使用 `asyncio.Queue` 在子线程（管道）与主事件循环（SSE 推送）之间桥接
- 管道在默认 `ThreadPoolExecutor` 中执行，不创建额外线程池
- 管道结束后通过 sentinel 值通知 async 侧停止迭代
- 线程内异常 MUST 传递到 async 侧并正确 re-raise

#### Scenario: 管道执行期间健康检查可达

- **WHEN** 提取请求正在执行（管道耗时 5 秒以上）
- **THEN** `/health` 端点在 100ms 内响应，不被提取管道阻塞

#### Scenario: 流式进度保持实时推送

- **WHEN** 管道各阶段完成
- **THEN** SSE 进度事件在阶段完成后立即推送到前端（延迟不超过 100ms），不等待全部阶段完成

#### Scenario: 管道异常正确传播

- **WHEN** 线程内管道抛出异常
- **THEN** async 侧捕获并转换为 SSE error 事件，连接正常关闭