## Context

当前系统管道：`文本 → OCR(可选) → LLM提取 → Geocode → GeoJSON → 静态渲染`，输出为单一静态地图，所有地名和路线同时呈现。此次变更在 LLM 提取环节增加时间维度，使前端可逐步推进展示战役进程。

约束：
- 不引入新的外部依赖
- 保持 `/api/extract` SSE 管道兼容（通过参数区分 mode）
- 现有 `CampaignExtract` 模型保持不变，新增模型与其共存
- 前端为单文件 `static/index.html`（~30KB），新 UI 组件内嵌其中

## Goals / Non-Goals

**Goals:**
- LLM 能从战役文本中提取有序事件序列（行军→战斗→撤退等）
- 前端提供逐步推进交互，路线和标记随步进动态生长
- GeoJSON 一次生成，前端按 step filter，避免每次步进都请求后端

**Non-Goals:**
- 不做自动播放（auto-play）
- 不引入时间轴拖拽 scrubbing（仅步进按钮+进度条）
- 不支持用户手动创建/编辑事件节点（纯 LLM 推断）
- 不改变 `/api/render` 端点行为（修正重渲染暂不支持时间线）

## Decisions

### 1. 数据模型：扩展现有而非替换

`CampaignExtract` 保持不变，新增 `CampaignTimeline(CampaignExtract)` 继承并添加 `events` 字段。每个 `TimelineEvent` 通过 `places_involved` 引用 `places` 中的地名，通过 `route_segment` 描述本事件新增的路线段。

**理由**：保持向后兼容，现有 `extract()` 调用者（如 `/api/render`、CLI）不受影响。

### 2. LLM 提取：独立函数 + 独立 Prompt

新增 `extract_timeline(text)` 函数，使用改良后的 system prompt。不改动现有 `extract()` 函数。

**Prompt 关键改动**：在现有规则基础上增加第 9 条——要求输出 `events` 数组，每个事件含 `seq`、`event_type`、`description`、`actors`、`places_involved`。

**备选方案**：在现有 `extract()` 中通过参数切换。被否决——两种 prompt 差异大，混在一起容易出 prompt 注入问题。

### 3. GeoJSON 生成：feature 级 step 标记

每个 GeoJSON feature 的 `properties` 中增加 `step` 字段（整数），表示该 feature 首次出现的事件序号。路线 feature 额外标注 `step_start` 和 `step_end`。

前端维护 `currentStep` 状态变量，渲染时通过 MapLibre `filter` 表达式过滤：`feature.properties.step <= currentStep`。

**理由**：GeoJSON 一次生成，前端纯 filter，O(1) 渲染切换，无需额外网络请求。

### 4. 前端状态管理：单一 currentStep 变量

不使用复杂状态管理库。`currentStep` 默认为最后一步（显示完整地图），用户点击「上一步」递减、「下一步」递增。地图通过 `map.setFilter()` 即时更新。

**备选方案**：每次步进调用 `/api/render`。被否决——增加延迟和服务器负载。

### 5. SSE 管道：通过 mode 参数切换

`/api/extract` 请求体新增可选字段 `mode: "timeline" | "static"`，默认 `"static"` 保持兼容。`mode=timeline` 时调用 `extract_timeline()`，最终 `result` 事件的 `geojson` 中 feature 携带 step 属性。

## Risks / Trade-offs

- **[LLM 质量]** Prompt 要求同时输出 places/routes 和 events 数组，可能增加 JSON 结构出错概率 → 通过 Pydantic 校验兜底，格式不合法返回 422
- **[事件粒度]** LLM 对事件切分粒度可能与用户预期不一致（太细或太粗）→ 接受初版误差，后续可通过 prompt 迭代优化，不做手动编辑
- **[地名一致性]** `TimelineEvent.places_involved` 必须是 `places` 数组中的地名，LLM 可能产生拼写不一致 → Prompt 中强调这条约束，Pydantic 不做校验（留给后续版本做后端校验）
- **[前端复杂度]** 新增 3 个 UI 组件（进度条、步进按钮、事件卡片），单文件 index.html 可能膨胀 → 本次接受膨胀，后续可拆分前端