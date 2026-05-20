## Context

当前 `/api/extract` 是标准的 HTTP POST → JSON 响应，整个管道（extract → geocode → geojson）在单个请求中同步完成，耗时 7-17 秒。前端只有一个 loading spinner，用户无法感知进度，也无法在管道中间介入纠正错误。

## Goals / Non-Goals

**Goals:**
- 后端通过 SSE 推送管道各阶段的完成事件
- 前端展示分阶段进度条（识别文字 → 提取结构 → 匹配地名 → 渲染地图）
- 提取结果面板可编辑：地名、路线、将领字段可修改
- 新增 `/api/render` 端点：接收修正后的结构化数据，跳过 extract+geocode，直接生成 GeoJSON
- 支持 Ctrl+Enter 提交文本
- 增强 Extractor Prompt 以处理混合内容

**Non-Goals:**
- 不做 WebSocket 实时双向通信（SSE 足够）
- 不做提取结果持久化存储
- 不改动 CHGIS 数据
- 不改动 PaddleOCR 模块

## Decisions

### 1. SSE 替代 WebSocket

**选择**: Server-Sent Events (SSE)
**理由**:
- 单向推送足够（服务端→前端），不需要客户端发送消息
- FastAPI 原生支持 `StreamingResponse`，无需额外依赖
- SSE 自动重连，断线后前端无需额外处理
- 比 WebSocket 更轻量，无协议升级开销

**替代方案**: WebSocket → 过度设计，双向通信不是必需的

### 2. 进度事件格式

每个阶段完成后推送一个 JSON 事件：

```
event: progress
data: {"stage": "ocr_done", "detail": "识别文字 (529字)", "ok": true}

event: progress
data: {"stage": "extract_done", "detail": "提取结构数据 (3地名, 2路线)", "ok": true}

event: progress
data: {"stage": "geocode_done", "detail": "匹配古地名 (2 CHGIS + 1 LLM)", "ok": true}

event: result
data: {"geojson": {...}, "extract": {...}}

event: error
data: {"stage": "extract", "message": "DeepSeek API 超时"}
```

事件类型: `progress`（阶段更新）、`result`（最终数据）、`error`（阶段失败）

### 3. `/api/render` 端点设计

接收前端修正后的提取数据，跳过 LLM 调用，直接 geocode + 生成 GeoJSON：

```
POST /api/render
Body: {
  "campaign_name": "...",
  "factions": [...],    // 用户可修改
  "places": [...],      // 用户可修改
  "routes": [...]       // 用户可修改
}
Response: { "geojson": {...} }
```

这样用户修改提取结果后点「重新渲染」只需 2-3 秒（仅 geocode），无需再等 LLM。

### 4. 前端可编辑面板实现

提取结果面板中，每个字段用 `contenteditable` 或 `input` 包裹：
- 地名列表：每个地名是一个可编辑 chip，点击可修改文本
- 路线：每条路线的 from/to/via 均可编辑
- 将领：每个将领名可编辑，支持新增/删除
- 修改后「重新渲染」按钮亮起，点击调用 `/api/render`

### 5. Extractor Prompt 增强

在现有 prompt 中增加以下规则：
- 「文本可能包含朝堂对话、人物议论等非军事内容，只从军事行动相关段落中提取信息」
- 「人物言论中假设或建议的行动（如"臣以为应从X出兵"）不应视为实际行军节点」
- 「如果文本中没有可确认的军事行动，返回空的 places 和 routes」

## Risks / Trade-offs

- **SSE 代理兼容性**: 某些反向代理可能缓冲 SSE 流 → 在响应头中添加 `X-Accel-Buffering: no` 和 `Cache-Control: no-cache`
- **可编辑面板复杂度**: contenteditable 在跨浏览器时行为不一致 → 使用普通 input 字段而非 contenteditable，避免兼容问题
- **Prompt 变更可能影响正常提取**: 更保守的提取策略可能导致漏提 → 保持提取规则温和，仅在 Prompt 中增加「注意区分」指令而非「禁止提取」