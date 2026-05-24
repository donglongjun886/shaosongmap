## Context

当前地图初始化时 style 对象内联定义，Phase 1 将其硬编码为纯色 `#f5f0e1` 背景。底图、箭头尺寸、标记样式三项各自独立，缺乏统一的 scale 感知协调机制。

## Goals / Non-Goals

**Goals:**
- 底图可在纯色（schematic）和低饱和 OSM（muted_osm）间切换，根据 scale 自动选择
- 箭头尺寸自适应数据范围，在不同 zoom 下保持屏幕占比可控
- 地名标记随 zoom 缩放，近看放大远看缩小
- 架构预留手动底图切换和山川河流符号层扩展点

**Non-Goals:**
- 不实现手动底图切换 UI
- 不实现山川河流符号渲染（Phase 3）
- 不更换瓦片服务商或引入新依赖
- 不改变 API 接口

## Decisions

### 1. 底图 Provider：动态 source/layer 管理

当前底图在 Map 构造函数的 `style` 参数中定义。MapLibre 不支持直接修改已初始化的 style object，但支持 `map.addSource` / `map.removeSource` / `map.addLayer` / `map.removeLayer` 运行时操作。

**方案**：初始化 style layers 为空数组，所有图层（含底图）在 `map.on('load')` 中统一添加。切换底图时 remove 旧底图 source+layer，add 新底图 source+layer，数据层不受影响。

Provider 注册表：

```javascript
const BASEMAP = {
  schematic: {
    id: 'schematic',
    sources: {},
    layers: [{ id: 'basemap-bg', type: 'background', paint: { 'background-color': '#f5f0e1' }, metadata: { basemap: true } }]
  },
  muted_osm: {
    id: 'muted_osm',
    sources: { 'basemap-osm': { type: 'raster', tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'], tileSize: 256, attribution: '© OSM' }},
    layers: [{ id: 'basemap-osm', type: 'raster', source: 'basemap-osm', paint: { 'raster-opacity': 0.25, 'raster-saturation': -1 }, metadata: { basemap: true } }]
  }
};
```

`metadata: { basemap: true }` 标记用于切换时识别和移除。

**备选方案**：
- `map.setStyle()` 全量重建：可靠但会清除所有 source/layer，需要重新添加数据层，增加闪烁
- 多个 Map 实例：浪费资源
- **选择动态 source/layer**：改动最小，数据层不受影响，无闪烁

### 2. 箭头自适应尺寸

当前固定米制（400/2000/5000m）不随数据范围调整。改为：

```python
diagonal_m = geographic_diagonal(place_coords)  # 数据包围盒对角线长度
scale_ratio = {'tactical': 0.20, 'battle': 0.08, 'strategic': 0.03}
body_len_m = diagonal_m * scale_ratio[scale]
# 最小像素保底：估算 40px 对应的地理距离
min_body_m = diagonal_m / viewport_px_diagonal * 40
body_len_m = max(body_len_m, min_body_m)
```

**备选方案**：
- 前端用 turf.js 计算：需要额外依赖，增加前端复杂度
- 后端接收 viewport_dimensions 参数：精确但需要额外 API 字段
- **选择后端基于数据范围计算**：最简单，不增加任何 API 变更

### 3. 箭头形状优化

```
旧形状: body 宽长比 1:2, head 占 27% (150/550)
新形状: body 宽长比 1:3.5, head 占 40%

视觉效果变化：
  旧: ┌──────────────┐
      │              │  body 400m × 200m (矮胖)
      │              │
      └──────┐       │
              >       head 150m
  新: ┌─────────────────────┐
      │                     │  body 更修长 (1:3.5)
      │                     │
      └──────────┐          │
                  >          head 占比更大 (40%)
```

### 4. Zoom 响应式标记

使用 MapLibre 表达式（非插值），基于 zoom 级别缩放标记大小：

```javascript
'circle-radius': ['step', ['zoom'],
  3, 5,   // zoom < 5  → 3px
  6, 8,   // zoom < 8  → 6px
  10, 12, // zoom < 12 → 10px
  14       // zoom ≥ 12 → 14px
]
```

**备选方案**：
- `interpolate` 线性插值：平滑但参数复杂
- **选择 `step` 分段**：简单明确，各 scale 区间边界清晰

### 5. TODO 占位：山川河流层

在 `map.on('load')` 之后添加占位代码：

```javascript
// TODO: Phase 3 山川河流符号层 (terrainSymbolSource / terrainSymbolLayer)
// 扩展点：在 basemap 和数据层之间插入 terrain 符号图层组
// 数据来源：LLM 提取地形实体 → geojson 生成 → 前端渲染
```

## Risks / Trade-offs

- muted_osm 在 zoom > 18 时 OSM 瓦片可能无数据 → 前端限制 maxZoom 为 18
- 数据范围对角线极小时（单点），`diagonal_m ≈ 0` → 箭头回退到最小默认值 100m
- 动态 source/layer 管理增加 load 回调复杂度 → 使用 `applyBasemap()` 单一函数集中管理
