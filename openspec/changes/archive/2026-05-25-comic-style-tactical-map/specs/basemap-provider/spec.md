# Basemap Provider 底图提供者 (Delta)

## MODIFIED Requirements

### Requirement: 底图提供者架构

系统 SHALL 支持可切换的底图提供者（Basemap Provider）架构，提供至少两种底图模式，并根据军事 scale 级别自动选择。架构 MUST 预留手动切换接口供后续扩展。

底图提供者 MUST 支持：
- `schematic`：纯色背景（仿古纸淡黄 `#f5f0e1`），不依赖任何外部瓦片服务。在 comic 主题（tactical 级）下扩展为纸纹理+地形色块组合底图
- `muted_osm`：低饱和 OpenStreetMap 瓦片（opacity 0.25，saturation -1），提供地形参照但不喧宾夺主

系统 SHALL 根据 scale 自动选择底图：
- tactical → `schematic`（comic 主题激活时叠加地形色块和纸纹理）
- battle → `muted_osm`
- strategic → `muted_osm`

底图切换 MUST 通过运行时动态添加/移除 MapLibre source 和 layer 实现，不重建地图实例，不影响数据层（地名、路线、部队箭头）。

架构 MUST 预留 `basemapMode` 状态变量，支持 `'auto'`（默认）和指定 provider ID 值，供后续手动切换 UI 使用。

#### Scenario: tactical 级别使用纯色底图

- **WHEN** 提取结果的 scale 为 `tactical`
- **THEN** 地图使用 `schematic` 纯色底图（`#f5f0e1`），不加载任何外部瓦片

#### Scenario: tactical 级别 comic 主题叠加地形色块

- **WHEN** 提取结果的 scale 为 `tactical` 且 comic 主题激活
- **THEN** schematic 底图之上额外渲染地形色块 fill layer 和纸纹理叠加层

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
