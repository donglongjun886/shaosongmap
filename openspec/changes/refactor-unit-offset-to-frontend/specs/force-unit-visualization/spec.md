## MODIFIED Requirements

### Requirement: 同名地多部队旗帜偏移

系统 SHALL 在后端为同坐标部队分配槽位序号（`_slot`），由前端根据当前实际地图 zoom 级别和渲染主题的图标尺寸，动态计算并应用地理偏移量。

后端 MUST：
- 检测同坐标的部队，按名称字母序分配 `_slot: 0/1/2/N`
- 不同坐标的部队各自独立编号，单部队 `_slot=0`
- 部队 feature 的坐标保持真实经纬度不变（不做度数偏移）

前端偏移 MUST：
- 使用 `map.getZoom()` 获取当前实际 zoom 级别计算 `m_per_px`
- 根据当前渲染主题取目标图标宽度（comic: 84px, banner: 26px）
- 目标像素间距 = 图标宽度 × 1.3
- 所有部队位于地点北侧，偏移量 = `(_slot + 1) * spacing_px * m_per_px * deg_per_m_lat`
- 监听 `map.on('moveend')` 事件，zoom 变化时自动重新计算

#### Scenario: 三个部队在同一地名

- **WHEN** 「焦文通部」「郦琼部」「王彦中军」的当前位置都关联到同一坐标
- **THEN** 后端分配 `_slot` 0/1/2，前端在 zoom 14 comic 主题下分别偏移 110px/220px/330px，互不重叠

#### Scenario: 只有一个部队在地名

- **WHEN** 仅「合扎猛安」的当前位置关联到「塬底」
- **THEN** `_slot=0`，前端偏移 1 倍间距，旗帜位于地点北侧

#### Scenario: zoom 缩放后像素间距保持不变

- **WHEN** 用户缩放地图从 zoom 14 到 zoom 10
- **THEN** 前端重新计算 `m_per_px`，度数偏移增大以保持相同的目标像素间距

## REMOVED Requirements

### Requirement: Scale 级别自适应旗帜

**Reason**: 方向线长度计算（`direction_len_m = diagonal_m * ratio`）保留在 `make_unit_geojson()` 中不变。仅移除 scale 驱动的像素偏移逻辑，由前端自适应替代。

**Migration**: 向后端 `make_unit_geojson()` 中添加 `_slot` 标记；前端新增 `_applyUnitOffsets()` 处理偏移。
