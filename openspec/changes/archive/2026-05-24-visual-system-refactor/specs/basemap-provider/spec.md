## ADDED Requirements

### Requirement: 底图提供者架构

系统 SHALL 支持可切换的底图提供者（Basemap Provider）架构，提供至少两种底图模式，并根据军事 scale 级别自动选择。架构 MUST 预留手动切换接口供后续扩展。

底图提供者 MUST 支持：
- `schematic`：纯色背景（仿古纸淡黄 `#f5f0e1`），不依赖任何外部瓦片服务
- `muted_osm`：低饱和 OpenStreetMap 瓦片（opacity 0.25，saturation -1），提供地形参照但不喧宾夺主

系统 SHALL 根据 scale 自动选择底图：
- tactical → `schematic`
- battle → `muted_osm`
- strategic → `muted_osm`

底图切换 MUST 通过运行时动态添加/移除 MapLibre source 和 layer 实现，不重建地图实例，不影响数据层（地名、路线、部队箭头）。

架构 MUST 预留 `basemapMode` 状态变量，支持 `'auto'`（默认）和指定 provider ID 值，供后续手动切换 UI 使用。

#### Scenario: tactical 级别使用纯色底图

- **WHEN** 提取结果的 scale 为 `tactical`
- **THEN** 地图使用 `schematic` 纯色底图（`#f5f0e1`），不加载任何外部瓦片

#### Scenario: battle 级别使用低饱和 OSM 底图

- **WHEN** 提取结果的 scale 为 `battle`
- **THEN** 地图使用 `muted_osm` 底图，OSM 瓦片以 25% 透明度、灰度化渲染

#### Scenario: strategic 级别使用低饱和 OSM 底图

- **WHEN** 提取结果的 scale 为 `strategic`
- **THEN** 地图使用 `muted_osm` 底图，提供大范围地理参照

#### Scenario: 底图切换不影响数据层

- **WHEN** 系统从 `schematic` 切换到底图 `muted_osm`（或反向）
- **THEN** 地图上的地名标记、行军路线、部队箭头保持显示，位置和样式不变

#### Scenario: 预留手动切换接口

- **WHEN** 开发者设置 `basemapMode = 'schematic'`（手动模式）
- **THEN** 系统使用指定底图，不再根据 scale 自动选择

### Requirement: Zoom 响应式地名标记

系统 SHALL 使用 MapLibre zoom 表达式动态调整地名标记的 circle-radius 和 text-size，确保在不同缩放级别下标记清晰可读且不重叠。

circle-radius MUST 按以下分段映射：
- zoom < 5 → 3px（远视角，极小标记）
- zoom 5-8 → 6px
- zoom 8-12 → 10px
- zoom ≥ 12 → 14px（近视角，战术细节）

text-size MUST 按以下分段映射：
- zoom < 5 → 9px
- zoom 5-8 → 11px
- zoom 8-12 → 13px
- zoom ≥ 12 → 15px

灰显（dim）标记的 circle-radius 应比正常标记小 2px。

#### Scenario: 战略级远视角下标记缩小

- **WHEN** 地图 zoom 为 5，scale 为 strategic
- **THEN** 地名 circle-radius 为 3px，text-size 为 9px，避免标记过大遮盖地形

#### Scenario: 战术级近视角下标记放大

- **WHEN** 地图 zoom 为 14，scale 为 tactical
- **THEN** 地名 circle-radius 为 14px，text-size 为 15px，近距离可清晰识别

#### Scenario: zoom 变化时标记平滑过渡

- **WHEN** 用户缩放地图从 zoom 8 到 zoom 12
- **THEN** 地名标记尺寸从 6px 逐步过渡到 10px（step 表达式自动插值）
