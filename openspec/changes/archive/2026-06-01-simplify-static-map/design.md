## Context

当前系统前端 MapLibre + 三层Canvas + roughjs + tacticalRenderer，后端支持 timeline/static 双模式。实际只需静态战役地图（地名 + 路线），全部砍掉多余架构。

## Goals / Non-Goals

**Goals:**
- 前后端简化为单一渲染路径：提取 → 编码 → MapLibre GeoJSON 渲染
- 删除所有时间轴、部队、箭头、scale 相关代码
- SSE 保留但仅推送进度，不做分步数据推送

**Non-Goals:**
- 地形阴影（后续）
- 部队标记聚合（无部队）
- API 版本兼容（旧版直接删）
- utils.js 深度清理（仅删引用，保留空函数）

## Decisions

### 1. SSE 保留 vs 改普通 JSON
选择：保留 SSE。理由：LLM 提取 + CHGIS 编码可能超过 30s，SSE 流式推送进度避免网关超时，同时给用户进度反馈。

### 2. 后端 prompt 简化范围
删除：events、unit_states、units.direction、scale 分类规则。保留：campaign_name、factions、places、routes、units（仅基本字段 name/faction/commander/troop_type/troop_count）。

### 3. 前端仅保留 MapLibre
删除三层 Canvas + roughjs。MapLibre 的 GeoJSON layer 直接渲染路线和地名标记，不再需要 Canvas 覆盖层。

## Risks / Trade-offs

| Risk | Mitigation |
|------|-----------|
| LLM 编造 routes 节点与 places 不一致 | Prompt 增加约束 + 后端校验过滤 |
| 删除文件后 map.js 引用断裂 | 全局搜索确认并清理 CanvasRenderer 调用 |
| utils.js 死代码 | 仅删除被删文件引用的函数 |
