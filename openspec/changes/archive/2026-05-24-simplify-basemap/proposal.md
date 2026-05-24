## Why

OSM 现代地图瓦片展示的街道、建筑与 900 年前的战场无关，在战术级历史战役可视化中反而干扰视觉。移除 OSM 底图替换为纯色背景，让读者的注意力聚焦在真正有价值的信息层（地名、行军路线、部队箭头）上。这是「示意图风格」渐进改造的 Phase 1。

## What Changes

- 地图初始化 style 对象中移除 `osm` raster 瓦片 source 和 `osm-layer` 图层
- 新增 `background` 类型图层，背景色 `#f5f0e1`（仿古纸淡黄）
- 所有数据层（places、routes、unit-arrows）保持不变，颜色无需调整
- **BREAKING**: 不再加载 OpenStreetMap 瓦片，离线环境也可正常渲染

## Capabilities

### New Capabilities
<!-- 无新增能力，纯视觉层替换 -->

### Modified Capabilities
- `campaign-map-rendering`: 底图需求从「OpenStreetMap 瓦片」改为「纯色背景」；地图渲染不再依赖外部瓦片服务

## Impact

- `static/index.html`: 地图初始化 style 对象，~12 行 → 2 行
- 无后端变更，无 API 变更，无依赖变更
- 不再请求 `tile.openstreetmap.org`，减少外部网络依赖
