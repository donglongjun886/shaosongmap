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

最终事件类型为 `result`，MUST 包含完整的 `geojson` 和 `extract` 数据。

#### Scenario: 正常管道进度推送

- **WHEN** 用户提交一段战役文本
- **THEN** 前端依次收到 `extract_done` → `geocode_done` → `result` 事件，进度条逐步点亮

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
