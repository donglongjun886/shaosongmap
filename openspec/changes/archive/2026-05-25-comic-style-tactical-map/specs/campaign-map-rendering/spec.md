# Campaign Map Rendering 战役地图渲染 (Delta)

## ADDED Requirements

### Requirement: Comic 主题地形色块图层

系统 SHALL 在 comic 主题（tactical 级）下渲染地形色块图层，以半透明色块标示山川河谷的示意位置。

地形色块 MUST：
- 渲染在底图之上、标记和路线之下（z-index 层级：底图 < 色块 < 路线 < 标记 < 标签）
- 通过 MapLibre `fill` layer 实现，source 为动态生成的 GeoJSON
- 每个色块半径为数据包围盒对角线的 5%（最小 500m，最大 5000m）
- 色块不可交互（无 click/hover 事件）

#### Scenario: 山脉和河流色块渲染

- **WHEN** comic 主题激活且战役数据包含 `place_type: mountain` 和 `place_type: river`
- **THEN** 地图上以地名坐标为中心渲染对应颜色的半透明圆形色块

#### Scenario: 地形色块在路线下方

- **WHEN** comic 主题激活且某地形色块与行军路线空间重叠
- **THEN** 路线线条始终渲染在色块上方，不被色块遮挡

### Requirement: Comic 主题箭头加粗与笔触感

系统 SHALL 在 comic 主题下将行军路线和方向箭头渲染为更粗壮的毛笔笔触风格。

箭头 MUST：
- 线宽为基础线宽的 1.5 倍（tactical 级约 3.5px）
- 颜色使用阵营色（由 CSS 变量驱动）
- 起笔端添加小圆点（直径 = 线宽 × 1.8）模拟毛笔顿笔
- 末端箭头尺寸放大 20%
- 通过 MapLibre line layer 的 `line-cap: round` 和 `line-width` 实现

#### Scenario: Comic 主题下金军箭头加粗变红

- **WHEN** comic 主题激活且行军路线涉及金军
- **THEN** 箭头线宽 3.5px，朱砂红色，起笔端有圆形顿笔点

### Requirement: Comic 主题印章叠加层

系统 SHALL 在 comic 主题下于地图容器右下角叠加一个不可交互的红色印章 SVG 元素。

印章 MUST：
- 位于地图容器右下角，距边缘 24px
- 用 `position: absolute` 的 div + 内联 SVG 实现
- 颜色 `#c23b22`，opacity 0.85
- 约 15 度旋转（CSS `transform: rotate(-15deg)`）
- 文字为战役名前 4 字（不足则全部显示），无战役名时不渲染
- `pointer-events: none`，不影响地图交互

#### Scenario: 印章显示

- **WHEN** comic 主题激活且 campaign_name 为「东坡塬遭遇战」
- **THEN** 印章显示「东坡塬遭」，右下角 24px 处

#### Scenario: 无战役名隐藏印章

- **WHEN** comic 主题激活但 campaign_name 为 null
- **THEN** 印章 div 存在但内容为空，不占视觉空间

### Requirement: Comic 主题地名标签光晕

系统 SHALL 在 comic 主题下通过 MapLibre text-halo 属性为地名标签添加半透明白色光晕，防止地形色块干扰文字可读性。

光晕 MUST：
- `text-halo-color`: `rgba(255,255,255,0.75)`
- `text-halo-width`: 2.5px（比默认值大 1px）
- `text-halo-blur`: 0.5px
- 仅 comic 主题下生效

#### Scenario: 标签在地形色块上可读

- **WHEN** comic 主题激活且标签「东坡塬」位于浅棕绿色块上方
- **THEN** 标签文字周围显示白色光晕，文字与色块边界清晰
