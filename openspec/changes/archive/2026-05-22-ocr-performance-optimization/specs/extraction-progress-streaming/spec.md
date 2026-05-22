## MODIFIED Requirements

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
