## MODIFIED Requirements

### Requirement: 底图提供者架构

系统 SHALL 支持可切换的底图提供者架构，提供至少两种底图模式，并根据军事 scale 级别自动选择。所有底图模式 MUST 叠加宣纸纹理（SVG noise filter），确保背景有纸张质感而非纯平面色块。

#### Scenario: 纯色底图叠加纹理

- **WHEN** 系统使用 `schematic` 纯色底图
- **THEN** 背景在 `#f2e8d5` 宣纸色之上叠加 SVG noise 颗粒纹理，呈现纸张质感

#### Scenario: OSM 底图叠加纹理

- **WHEN** 系统使用 `muted_osm` 低饱和 OSM 底图
- **THEN** 在 OSM 瓦片之上叠加半透明纹理层，使现代地图数据融入古地图氛围