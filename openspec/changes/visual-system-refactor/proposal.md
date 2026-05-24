## Why

Phase 1 去掉了 OSM 底图，但暴露出两个问题：(1) 部队箭头和地名标记的比例在不同缩放级别下失调——两个相距 500km 的地名间箭头小到看不清，而 2km 内的战术箭头又大到爆炸；(2) 战略/战役级地图缺少地形参照，需要一个可切换的底图架构。本次重构统一解决这两个问题，并为后续山川河流符号预留扩展点。

## What Changes

- **底图 Provider 架构**：定义 `schematic`（纯色）和 `muted_osm`（低饱和 OSM，opacity 25%）两种底图模式，根据 scale 自动选择（tactical→schematic，battle/strategic→muted_osm），预留手动切换接口
- **箭头尺寸自适应**：从固定米制改为「数据范围对角线 × scale 系数」，确保箭头在屏幕上占比可控；同时优化形状比例（宽长比 1:3.5，头部占 40%），视觉上更修长、方向感更强
- **Zoom 响应式标记**：地名 circle-radius 和 text-size 使用 MapLibre zoom 表达式，近看放大、远看缩小，避免密集区域重叠或远距不可见
- **地图初始化重构**：style 对象改为空 layers，所有图层（含底图）在 `map.on('load')` 中动态添加，支持运行时切换底图
- **TODO 占位**：terrainSymbolLayer 架构预留，标记为 Phase 3

## Capabilities

### New Capabilities
- `basemap-provider`: 底图提供者架构，支持运行时切换底图，scale 自动选择，预留手动切换接口

### Modified Capabilities
- `campaign-map-rendering`: 底图需求从「纯色背景」改为「可切换底图」；地名标记增加 zoom 响应式尺寸
- `force-unit-visualization`: 箭头尺寸从固定米制改为数据范围自适应；箭头形状比例优化（宽长比 1:3.5，头部 40%）

## Impact

- `static/index.html`: 地图初始化重构、basemap 切换逻辑、zoom 表达式、图层动态管理
- `app.py`: `_make_block_arrow_polygon` 形状参数、`_make_unit_geojson` 自适应尺寸计算、`_compute_unit_offsets` 间距调整
- 无 API 变更，无数据模型变更，无新依赖
