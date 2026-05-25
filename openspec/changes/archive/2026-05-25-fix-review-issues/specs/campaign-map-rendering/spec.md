## ADDED Requirements

### Requirement: 行军路线虚线样式优化

系统 SHALL 调整行军路线的虚线参数以减少视觉断裂感，同时保持古地图风格。

路线 `line-dasharray` MUST：
- 默认模式（battle/strategic）：`[6, 3]`（原 `[8, 4]`，实线段从 8px 缩至 6px，间隙从 4px 缩至 3px）
- Comic 主题（tactical）：`[6, 3]`（原 `[10, 5]`）

此变更 MUST 不改变路线的颜色、线宽、opacity 等其他 paint 属性。

#### Scenario: 默认模式下路线虚线更紧凑

- **WHEN** 地图在 battle 或 strategic 级别渲染行军路线
- **THEN** 路线虚线使用 `[6, 3]` 参数，视觉上比 `[8, 4]` 更连续

#### Scenario: Comic 主题下路线虚线同步调整

- **WHEN** comic 主题激活（tactical 级）渲染行军路线
- **THEN** 路线虚线同样使用 `[6, 3]`，与 comic 主题的加粗线宽（3.5px）配合

### Requirement: 行军路线端点锚点标记

系统 SHALL 在每条行军路线的起止点渲染小型圆形锚点标记，使路线与地名/部队标记之间的空间连接关系更清晰。

锚点 MUST：
- 渲染在路线首末坐标处，通过独立的 `route-anchors` GeoJSON source 和 circle layer 实现
- 颜色为朱砂红 `#c23b22`，opacity 0.5
- 半径 3px（circle-radius），无描边
- 不可交互（无 click/hover 事件）
- 图层位于 `route-lines` 之上、地名标记之下
- 仅在 route features 数量 > 0 时渲染

锚点数据 MUST 在前端从路线的 LineString 坐标中提取：首坐标为首点、末坐标为末点。若路线仅含一个坐标（退化为点），则不生成锚点。

#### Scenario: 单条路线的首末锚点

- **WHEN** 地图渲染一条从「黄龙岭」到「岭北」的路线
- **THEN**「黄龙岭」和「岭北」坐标处各显示一个 3px 朱砂色小圆点，标识路线起止

#### Scenario: 多条路线各有独立锚点

- **WHEN** 地图渲染三条行军路线
- **THEN** 每条路线的首末点各有一个锚点，总计六个锚点

#### Scenario: 无路线时不渲染锚点层

- **WHEN** 战役数据无行军路线
- **THEN** `route-anchors` 的 GeoJSON source 包含空 FeatureCollection，circle layer 不渲染任何内容

#### Scenario: Comic 主题下锚点同样渲染

- **WHEN** comic 主题激活，地图上存在行军路线
- **THEN** 锚点 circle layer 正常渲染，样式与默认模式一致
