## ADDED Requirements

### Requirement: 单一静态地图渲染

系统 SHALL 仅支持一种地图渲染模式：静态战役地图，展示地名标记和行军路线。

前端 MUST 使用 MapLibre GL JS 的 GeoJSON 图层直接渲染，不依赖 Canvas 覆盖层。

#### Scenario: 提取并渲染静态地图

- **WHEN** 用户输入战役文本并点击生成
- **THEN** 系统返回包含地名标记和行军路线的 GeoJSON，MapLibre 渲染静态地图

### Requirement: SSE 进度推送

系统 SHALL 通过 SSE 流式推送提取和地理编码进度，最终返回完整结果。

SSE 事件 MUST 包含：`progress`（阶段进度）和 `result`（最终数据）。

#### Scenario: 推送处理进度

- **WHEN** LLM 提取完成
- **THEN** 前端收到 `progress` 事件，更新进度指示器

### Requirement: LLM 简化提取

LLM 提示词 SHALL 仅提取以下字段：`campaign_name`、`factions`、`places`、`routes`、`units`(基本字段)。

提示词 MUST 不包含：`events`、`unit_states`、`units.direction`、`scale` 分类规则。

#### Scenario: 提取战役文本

- **WHEN** 输入包含行军路线和地名的战役文本
- **THEN** LLM 返回结构化 JSON，仅含地名、路线、阵营信息

### Requirement: 删除部队渲染

系统 SHALL 不在前端渲染部队标记。

后端 MUST 删除 `unit_banner.py` 模块。前端 MUST 不生成部队 GeoJSON。

#### Scenario: 生成地图无部队标记

- **WHEN** 渲染静态战役地图
- **THEN** 地图上仅显示地名三角/圆点和行军路线，无部队旗杆或图标

## REMOVED Requirements

### Requirement: 时间轴模式
**Reason**: 简化架构，不再需要时间轴逐步展示
**Migration**: 删除 extract_timeline()、timeline UI、CanvasRenderer.setTimeline

### Requirement: Scale 分级
**Reason**: 仅保留一种大地图模式
**Migration**: 删除 scale 分类规则、前端 scale 分叉路由

### Requirement: 部队进攻箭头
**Reason**: 静态地图不需要箭头指向
**Migration**: 删除 direction_target、offset_point、燕尾箭头绘制

### Requirement: Canvas 渲染层
**Reason**: MapLibre GeoJSON 图层可独立完成渲染
**Migration**: 删除 canvasRenderer.js、terrainRenderer.js、tacticalRenderer.js、roughjs
