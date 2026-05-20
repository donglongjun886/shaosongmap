## Why

当前管道耗时 7-17 秒，用户面对单一 spinner 完全不知道发生了什么事，也无法在中间环节纠正错误。OCR 识别错误或 LLM 提取偏差会直接导致地图标记错位，但用户只能清空重来，挫败感强。

## What Changes

- **SSE 分阶段进度推送**：后端在提取管道的每个阶段完成后通过 Server-Sent Events 推送进度事件，前端逐步点亮进度条（识别文字 → 提取结构 → 匹配地名 → 渲染地图）
- **提取结果可编辑面板**：地名列表、行军路线、将领信息变为可编辑字段，用户可修正后点「重新渲染」更新地图，无需重跑整个管道
- **键盘快捷键**：Ctrl+Enter 提交、Esc 关闭 popup
- **增强 Extractor Prompt**：增加对非战役内容（朝堂对话、人物议论）的识别和忽略指令

## Capabilities

### New Capabilities
- `extraction-progress-streaming`: SSE 事件推送，管道的每个阶段完成时向前端推送进度状态，替换单一 loading spinner

### Modified Capabilities
- `campaign-map-rendering`: 新增可编辑提取结果面板（修正地名/路线后重新渲染）；新增键盘快捷键交互；新增分阶段进度展示 UI
- `campaign-text-extraction`: 增强 system prompt，处理混合内容（战役+对话+议论）场景，减少幻觉提取

## Impact

- `app.py`: `/api/extract` 端点改为 SSE 流式响应；新增 `/api/render` 端点接收修正后的数据直接渲染地图（跳过提取+geocode）
- `shaosongmap/extractor.py`: 更新 system prompt
- `static/index.html`: 新增进度条 UI、可编辑结果面板、键盘事件绑定
