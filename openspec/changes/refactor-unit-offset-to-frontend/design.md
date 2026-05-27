## Context

当前架构中，`compute_unit_offsets()` 在 Python 后端计算部队坐标偏移，硬编码了 zoom 级别和像素间距，将度数偏移写入 GeoJSON 返回给前端。前端直接渲染这些被修改过的坐标，完全不知道原始锚点在哪里。

问题链条：
1. 后端假设 zoom 14 (tactical) 下图标间距为 110px
2. 实际上 comic 图标 84px 宽，banner 图标 25.6px 宽，完全不同
3. 用户缩放地图后 zoom 变化，但偏移量已在 GeoJSON 中固定
4. 改间距要提交后端代码、跑 CI、等 hot reload

**约束**：不能引入新的前端框架/构建工具（保持零依赖 SPA），MapLibre 4.7.1 是唯一的地图库。

## Goals / Non-Goals

**Goals:**
- 后端只返回数据：真实坐标 + 同位置槽位序号 `_slot: 0/1/2`
- 前端根据当前实际 zoom 和当前主题图标尺寸计算偏移
- zoom 变化时自动重新计算，图标不重叠
- 删除 `compute_unit_offsets()` 及对应测试类

**Non-Goals:**
- 不改变部队数据模型（UnitState、ForceUnit、GeoFeature 不变）
- 不引入 Marker API（保持 symbol layer 渲染性能）
- 不改变非 comic 主题的图标样式
- 不做同级多部队的水平排列（仍沿南北方向）

## Decisions

### Decision 1: 前端用精确像素偏移，转度数后修正 GeoJSON 坐标

**方案**：在 `updateMap()` 中，对每个部队点，根据 `map.getZoom()` 计算 `m_per_px`，乘以目标像素间距，转为度数偏移，加到 GeoJSON 坐标上。

```javascript
// 伪代码
var zoom = map.getZoom();
var midLat = computeMidLat(unitFeatures);
var mPerPx = 156543 * Math.cos(midLat * Math.PI / 180) / Math.pow(2, zoom);
var iconPx = isComicTheme ? 84 : 26; // 实际渲染尺寸
var spacingPx = iconPx * 1.3; // 30% 间隙
var degPerMeterLat = 1 / 111320;
var slotGroups = groupBySameCoord(unitFeatures);
slotGroups.forEach(function(features) {
  features.forEach(function(f, i) {
    f.geometry.coordinates[1] += (i + 1) * spacingPx * mPerPx * degPerMeterLat;
  });
});
```

**替代方案及淘汰原因**：
- ~~MapLibre `icon-translate`~~：该属性以屏幕像素为单位，但无法按 feature 分别设置（不支持数据驱动），同坐标所有图标平移相同量，不能展开为列
- ~~MapLibre `icon-offset`~~：相对锚点的偏移，单位是 icon 尺寸的倍数，无法精确控制像素间距，且同样不支持数据驱动
- ~~Marker API~~：每个 marker 是独立 DOM 元素，对于频繁渲染/更新的大量部队不可取

### Decision 2: zoom 变化监听用 `moveend` 事件节流

**方案**：监听 `map.on('moveend')` 事件（包含 zoom 和 pan），debounce 100ms 后重新计算偏移并 `setData()`。

**理由**：`zoom` 事件每个 frame 触发一次，过于频繁。`moveend` 在用户操作停止后触发，重新计算偏移 + setData 对性能无感。

### Decision 3: comic 和 banner 模式用同一份偏移后的数据

**方案**：偏移计算在 `updateMap()` 中完成，先复制一份 GeoJSON 坐标，再加偏移，然后将修正后的 features 分别喂给 `unit-banners` 和 `comic-unit-icons` 源。

**理由**：两个源使用相同的锚点坐标，差异仅在图标渲染样式。偏移只需算一次。

### Decision 4: 后端 `_slot` 标记方案

**方案**：`make_unit_geojson()` 返回的 features 中，同坐标部队的 `properties._slot` 设为 `0, 1, 2...`（按部队名排序以保证确定性）。不同坐标或单部队的 `_slot` 为 0。

替代方案：在 `make_unit_geojson()` 返回前直接分组打标，不新增独立函数。

## Risks / Trade-offs

- **[R]** 大量部队 + 频繁缩放时，每次 `moveend` 都重新计算偏移和 setData → **[M]** `moveend` 频率低（操作停止后一次），偏移计算是 O(n) 纯数值运算，setData 是 MapLibre 高性能路径
- **[R]** 方向线坐标需跟随 → **[M]** 方向线是 LineString，从锚点坐标出发。锚点移动后方向线起点也变化。`make_unit_banner_features()` 返回的 LineString 坐标在 `updateMap()` 中同样修正
- **[R]** comic 图标单独渲染（`_renderComicUnitMarkers` 有自己的 iconFeatures 生成）→ **[M]** 在 `_renderComicUnitMarkers` 调用前先对 `unitBannerFeatures` 做偏移，保持一致
- **[R]** 向后兼容：旧 API 返回的 GeoJSON 不含 `_slot` 字段 → **[M]** 前端能处理缺失 `_slot` 的情况（回退到不偏移）

## Migration Plan

1. 前端先实现 `_applyUnitOffsets()` 和 `map.on('moveend')` 监听 → 确保偏移逻辑正确
2. 后端删除 `compute_unit_offsets()` → 改为返回真实坐标 + `_slot`
3. 更新测试
4. 部署：新前后端同时上线（前端兼容旧 `_slot` 缺失）

## Open Questions

- （无）所有技术决策已在上述分析中确定
