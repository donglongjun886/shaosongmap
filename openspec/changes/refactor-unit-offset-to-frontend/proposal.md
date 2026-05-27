## Why

同坐标部队偏移计算目前在后端 `unit_banner.py` 中完成，需要硬编码 zoom 级别和图标尺寸来换算像素偏移。连续两次修复（65px→110px）均因后端不知道前端实际渲染的图标类型和尺寸而猜错。根本矛盾：**展示层问题在数据层解决，后端不可能知道前端的渲染参数**。

## What Changes

- **BREAKING**: 移除 `compute_unit_offsets()` 函数，后端不再计算任何坐标偏移
- 后端仅标记同坐标部队的槽位序号（`_slot: 0/1/2/N`），坐标保持真实经纬度
- 前端新增 `applyUnitOffsets()` 函数，在 `updateMap()` 中根据**实际 zoom** 和**当前主题的图标尺寸**计算像素偏移，动态修改 GeoJSON 坐标
- 前端监听 `map.on('zoom')` 事件，zoom 变化时重新计算偏移，实现自适应
- 前端 `_renderComicUnitMarkers()` 同步应用同样的偏移逻辑
- 方向线起止点坐标跟随偏移后的锚点更新

## Capabilities

### New Capabilities

- `frontend-unit-offset`: 前端自适应部队偏移计算——根据实时 zoom 和当前渲染主题的图标尺寸，在 GeoJSON 数据源设置前动态计算经纬度偏移

### Modified Capabilities

- `force-unit-visualization`: "同名地多部队旗帜偏移" 需求改为前端自适应计算，移除后端 `compute_unit_offsets`

## Impact

- `shaosongmap/services/unit_banner.py` — 删除 `compute_unit_offsets`，`make_unit_geojson` 改为返回真实坐标 + `_slot` 序号
- `static/js/map.js` — 新增 `_computeSlotOffsets()` 和 `_applyUnitOffsets()`，修改 `updateMap()` 和 `_renderComicUnitMarkers()` 的数据处理流程
- `tests/test_unit_banner.py` — 删除 `TestComputeUnitOffsets` 类（5 个测试），新增 `test_slot_assignment` 测试
- `tests/test_frontend_utils.py` — 新增前端偏移计算纯函数测试
