## REMOVED Requirements

### Requirement: 时间轴交互
**Reason**: 仅保留静态地图，时间轴逐步展示功能删除
**Migration**: 删除 timeline UI、stepTo()、applyTimelineFilters() 中的 timeline 逻辑

### Requirement: 部队旗帜标记
**Reason**: 不再展示部队标记
**Migration**: 删除 unit-banner 相关 MapLibre layer、CanvasRenderer 部队渲染

### Requirement: 多 Scale 渲染
**Reason**: 仅保留一种地图模式
**Migration**: 删除 scale 分叉路由、scale 相关样式配置

### Requirement: Canvas 地形渲染
**Reason**: 不再使用 Canvas 渲染地形
**Migration**: 删除 terrainRenderer.js
