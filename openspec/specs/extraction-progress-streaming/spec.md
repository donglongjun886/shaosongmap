# Extraction Progress Streaming 分阶段进度推送

## Purpose

通过 Server-Sent Events (SSE) 在提取管道各阶段完成后向前端推送进度事件，替换单一 loading spinner，让用户感知管道进展。

## Requirements

### Requirement: SSE 分阶段进度推送

系统 SHALL 通过 Server-Sent Events 在提取管道的每个阶段完成后向前端推送进度事件，替代单一 loading spinner。

管道阶段序列：
1. `ocr_done` — OCR 文字识别完成（仅截图上传流程触发）
2. `extract_done` — LLM 结构化提取完成
3. `geocode_done` — 古地名坐标匹配完成
4. `render_done` — GeoJSON 生成完成，地图可渲染

每个进度事件 MUST 包含：
- `stage`: 阶段标识符
- `detail`: 中文描述（如「识别文字 (529字)」）
- `ok`: 该阶段是否成功
- `elapsed_ms`: 该阶段的独立耗时（整数，单位毫秒）

最终事件类型为 `result`，MUST 包含完整的 `geojson` 和 `extract` 数据，以及 `elapsed` 耗时分解对象：
- `extract_ms`: 提取阶段耗时
- `geocode_ms`: 地理编码阶段耗时
- `render_ms`: 渲染阶段耗时
- `total_ms`: 管道总耗时

服务端 MUST 通过 logging 在每个阶段完成时输出耗时日志，管道全部完成时输出汇总日志。

#### Scenario: 正常管道进度推送

- **WHEN** 用户提交一段战役文本
- **THEN** 前端依次收到 `extract_done` → `geocode_done` → `result` 事件，每个进度事件包含 `elapsed_ms`，最终 result 包含 `elapsed` 对象

#### Scenario: 截图上传流程包含 OCR 阶段

- **WHEN** 用户上传截图后提交
- **THEN** 前端依次收到 `ocr_done` → `extract_done` → `geocode_done` → `result` 事件

#### Scenario: 某阶段失败

- **WHEN** 管道中某个阶段失败（如 LLM API 超时）
- **THEN** 后端发送 `error` 事件，包含 `stage` 和 `message` 字段，前端停止进度条并在对应阶段显示红色 ✗

### Requirement: 修正后数据重新渲染端点

系统 SHALL 提供 `POST /api/render` 端点，接收用户修正后的战役提取数据（跳过 LLM 提取步骤），直接执行 geocode 并返回 GeoJSON。

请求体 MUST 包含：
- `campaign_name`: 战役名称（可为 null）
- `factions`: 阵营列表
- `places`: 地名列表
- `routes`: 行军路线列表

#### Scenario: 修正地名后重新渲染

- **WHEN** 用户在前端修改了地名列表中的某地名（如将 OCR 错误的「唐川」改为「唐州」），点击「重新渲染」
- **THEN** 系统使用修正后的地名重新 geocode，返回更新后的 GeoJSON，地图刷新

#### Scenario: 重新渲染不调用 LLM

- **WHEN** 调用 `/api/render`
- **THEN** 管道跳过 `extract` 步骤，直接从数据校验 → geocode → GeoJSON，耗时不超过 3 秒

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
