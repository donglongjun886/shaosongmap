## ADDED Requirements

### Requirement: 前端自适应部队偏移计算

系统 SHALL 在前端根据当前地图 zoom 级别和渲染主题的图标尺寸，动态计算同坐标部队的地理偏移量，替代后端硬编码像素间距。

偏移计算 MUST：
- 在 `updateMap()` 和 `_renderComicUnitMarkers()` 调用前完成坐标修正
- 使用 `map.getZoom()` 获取当前实际 zoom 级别（非 scale 字符串）
- 根据当前主题取图标渲染宽度：comic 主题 84px，banner 主题 26px
- 目标像素间距 = 图标宽度 × 1.3（保证 30% 可见间隙）
- 使用 Web Mercator 标准公式 `m_per_px = 156543 * cos(mid_lat) / (2^zoom)` 将像素间距转为度数偏移
- 同坐标部队按 `_slot` 序号（0/1/2/N）放置在地点北侧：偏移量 = `(_slot + 1) * spacing_deg`
- 所有部队坐标的经度分量不变（仅沿南北方向展开）

#### Scenario: 单部队 tactical comic 主题偏移

- **WHEN** 当前 zoom = 14，comic 主题激活，一支部队锚点位于 (114, 34)，`_slot=0`
- **THEN** 该部队图标位于地点以北约 110 像素处（约 84×1.3 = 109 像素），与地点图标不重叠

#### Scenario: 三部队同一地点按槽位展开

- **WHEN** 当前 zoom = 14，comic 主题激活，三支部队锚点位于同一坐标，`_slot` 分别为 0/1/2
- **THEN** 三支部队图标分别位于地点以北 110px、220px、330px 处，互不重叠

#### Scenario: zoom 缩放后自动重新计算偏移

- **WHEN** 用户将地图从 zoom 14 缩放到 zoom 10
- **THEN** `moveend` 事件触发后，所有部队的度数偏移量按 zoom 10 的 `m_per_px` 重新计算，像素间距保持目标值

#### Scenario: battle 级别使用 banner 图标尺寸

- **WHEN** 当前非 comic 主题（battle/strategic），一支部队锚点位于某地点
- **THEN** 使用 banner 图标宽度 26px 计算间距（26×1.3 ≈ 34px），比 comic 模式更紧凑

### Requirement: 后端槽位标记

系统 SHALL 在后端 `make_unit_geojson()` 中为每个部队 feature 添加 `_slot` 属性（整数，从 0 开始），标记该部队在同坐标部队中的排序位置。不同坐标的部队各自独立编号。

槽位标记 MUST：
- `_slot` 属性写入 feature 的 `properties` 字典中
- 同坐标部队按部队名称字母序排序后分配序号（保证确定性）
- 单部队或不同坐标部队的 `_slot` 均为 0
- `make_unit_banner_features()` 返回的 Point 和 LineString feature 均携带相同的 `_slot`

#### Scenario: 两支部队同坐标

- **WHEN** 「郦琼部」和「焦文通部」的当前位置都关联到同一坐标 (114, 34)
- **THEN** 按名称排序后「焦文通部」`_slot=0`，「郦琼部」`_slot=1`

#### Scenario: 单部队独享坐标

- **WHEN** 仅「合扎猛安」关联到坐标 (112, 32)
- **THEN** 该部队的 `_slot=0`

#### Scenario: 两部队不同坐标各得 _slot=0

- **WHEN** 「焦文通部」位于 (114, 34)，「娄室中军」位于 (112, 32)
- **THEN** 两支部队的 `_slot` 均为 0
