# Force Unit Visualization 部队可视化 (Delta)

## MODIFIED Requirements

### Requirement: 部队旗帜标记地图渲染

系统 SHALL 在地图上以**兵牌卡片**（Canvas 2D 圆角矩形 + 双层边框 + 顶部色条）渲染部队，替代原有的 MapLibre symbol layer 双线套框旗帜标记。

兵牌 MUST：
- 使用 Canvas 2D 绘制，而非 MapLibre `image` type symbol layer
- 圆角半径 12px，外边框 3px 阵营色，内边框 1px 墨色
- 顶部 12px 高阵营色色条标识
- 字体：14px 'Noto Serif SC'，墨色，居中
- 阴影：Canvas `dropShadow(2px, 3px, 4px, rgba(0,0,0,0.25))`
- 宋军靛蓝 `#2b4c7e`，金军朱砂红 `#c23b22`，未知墨色 `#2c2c2c`
- 进攻箭头从兵牌位置出发，线宽 14px，3:2 头部宽高比，带微弧贝塞尔路径
- 通过 `map.project([lng, lat])` 获取像素坐标，在 rAF 循环中绘制
- 方向指示线合并进箭头（兵牌→箭头为同一视觉元素）

#### Scenario: 部队旗帜随阵营着色

- **WHEN** 系统渲染宋军阵营的「焦文通部」和金军阵营的「合扎猛安」
- **THEN** 前者兵牌为靛蓝色系，后者为朱砂红色系

#### Scenario: 交战状态兵牌边框变红

- **WHEN** 时间线推进到步骤 3，焦文通部状态为 `engaging`
- **THEN** 焦文通部兵牌外边框切换为亮红 `#e63946`，同时触发脉冲动画

#### Scenario: 部队兵牌文本标签

- **WHEN** 部队兵牌渲染在地图上
- **THEN** 兵牌卡片内显示部队名称（如「焦文通部」），字体为 Noto Serif SC，墨色

#### Scenario: 溃散状态兵牌灰显

- **WHEN** 部队状态为 `routing`
- **THEN** 兵牌 opacity 在 3 个步骤内从 1.0 递减到 0，箭头碎裂为散点

#### Scenario: 部队在当前步骤无状态记录

- **WHEN** 时间线推进到步骤 3，郦琼部在步骤 3 无 UnitState 记录但在步骤 2 有记录
- **THEN** 郦琼部兵牌沿用步骤 2 的位置、方向和状态，不影响其他部队的正常更新

## REMOVED Requirements

### Requirement: Comic 主题部队标记样式

**Reason**: Comic 主题的阵营色填充矩形框+白色文字样式被 Canvas 兵牌卡片统一替代。所有主题的部队渲染走同一 Canvas 代码路径，通过配置参数区分样式（而非独立的 MapLibre icon 生成逻辑）。

**Migration**: 原 comic 主题部队标记的视觉参数（阵营色、尺寸、边框）保留在 Canvas 渲染器的主题配置中，删除 MapLibre `image` type symbol layer 的 comic icon 离线生成代码（`_renderComicUnitMarkers` 等函数）。
