# comic-style-tactical-theme Specification

## Purpose
TBD - created by archiving change comic-style-tactical-map. Update Purpose after archive.
## Requirements
### Requirement: 漫画主题按 Scale 激活

系统 SHALL 仅在 tactical scale 级别激活绍宋漫画视觉主题（`.theme-comic`），battle 和 strategic 级别保持现有汉代驻军图视觉体系不变。

主题切换 MUST：
- 在管道返回 scale 结果后自动判断并应用
- Tactical 级 map 容器添加 CSS class `.theme-comic`
- Battle/strategic 级不添加该 class
- 用户编辑后重新渲染时重新判断 scale 并切换主题

#### Scenario: Tactical 级战役激活漫画主题

- **WHEN** 管道返回 scale 为 `tactical`
- **THEN** 地图容器获得 `.theme-comic` class，所有漫画主题样式生效

#### Scenario: Battle 级战役不激活漫画主题

- **WHEN** 管道返回 scale 为 `battle`
- **THEN** 地图容器不添加 `.theme-comic` class，使用现有驻军图样式

### Requirement: 阵营色系统

系统 SHALL 在 comic 主题下定义阵营色 CSS 自定义属性，驱动部队标记、箭头、路线的着色。

阵营色映射 MUST：
- 宋军阵营：靛蓝 `#2b4c7e`（`--faction-song`）
- 金军阵营：朱砂红 `#c23b22`（`--faction-jin`）
- 未知/其他阵营：墨色 `#2c2c2c`（`--faction-unknown`）
- 交战状态覆盖色：亮红 `#e63946`（`--status-engaging`）

所有需要阵营区分的视觉元素 MUST 通过 CSS 变量引用阵营色，而非硬编码颜色值。

#### Scenario: 金军部队使用红色系

- **WHEN** comic 主题激活且部队阵营为金军
- **THEN** 该部队的标记框、方向箭头、路线均使用 `--faction-jin` 朱砂红色系渲染

#### Scenario: 宋军部队使用蓝色系

- **WHEN** comic 主题激活且部队阵营为宋军
- **THEN** 该部队的标记框、方向箭头、路线均使用 `--faction-song` 靛蓝色系渲染

#### Scenario: 交战状态覆盖阵营色

- **WHEN** 部队状态为 `engaging` 且阵营为宋军
- **THEN** 标记框边框使用 `--status-engaging` 亮红色，填充仍保留宋军蓝

### Requirement: 地形色块渲染

系统 SHALL 在 comic 主题下根据 `place_type` 字段以半透明色块渲染地形区域，仅 tactical 级显示。

地形色块映射 MUST：
- `mountain` / `mountain_pass`：浅棕绿色块 `rgba(139,119,101,0.12)`
- `river`：浅蓝色块 `rgba(100,149,237,0.15)`
- `valley` / `region`：浅黄色块 `rgba(218,195,125,0.12)`
- 色块以地名坐标为中心，半径为数据包围盒对角线的 5%
- 无 `place_type` 或类型无法匹配时，不生成色块

色块 MUST 渲染在地图数据的底层（z-index 低于标记和路线），不遮挡任何交互元素。

#### Scenario: 战场地形色块渲染

- **WHEN** comic 主题激活且战役包含 `place_type: mountain` 的「东坡塬」和 `place_type: river` 的「干涸河沟」
- **THEN** 地图上东坡塬坐标处显示浅棕绿色圆形色块，干涸河沟坐标处显示浅蓝色圆形色块

#### Scenario: 无地形类型时不生成色块

- **WHEN** 某地名的 `place_type` 为 `city` 或 `null`
- **THEN** 不为该地名生成地形色块

### Requirement: 红色印章装饰

系统 SHALL 在 comic 主题下于地图容器右下角渲染一个红色印章 SVG 装饰。

印章 MUST：
- 颜色为朱砂红 `#c23b22`，opacity 0.85
- 正方形边框，白文风格（文字镂空，边框填充）
- 文字内容为战役名（最多 4 字），超出时截断前 4 字
- 约 15 度旋转（CSS transform rotate）
- 尺寸约 48×48px
- 不可交互（pointer-events: none）

#### Scenario: 印章显示战役名

- **WHEN** comic 主题激活且战役名为「东坡塬之战」（5 字）
- **THEN** 印章内显示「东坡塬之」，截断为 4 字

#### Scenario: 无战役名时不显示印章

- **WHEN** comic 主题激活但 campaign_name 为 null
- **THEN** 印章区域为空，不渲染

### Requirement: Tactical 级宋体标注

系统 SHALL 在 comic 主题下将地图所有文字标签字体切换为宋体系列。

字体堆栈 MUST：`"SimSun", "Songti SC", "Noto Serif SC", serif`

此变更 MUST 仅影响 tactical 级地图上的地名标签、部队名称、popup 文字，不影响左侧面板的字体。

#### Scenario: Tactical 地图使用宋体

- **WHEN** comic 主题激活
- **THEN** 地图上所有 MapLibre 文字标签使用宋体渲染，左侧面板保持楷体不变

### Requirement: 地名标签半透明白底

系统 SHALL 在 comic 主题下为地名标签添加半透明白色背景框，防止地形色块干扰文字可读性。

标签背景 MUST：
- 背景色 `rgba(255,255,255,0.75)`
- 圆角 2px
- 内边距 2px 4px
- 通过 MapLibre `text-halo-color` 和 `text-halo-width` 实现

#### Scenario: 地名标签在地形色块上可读

- **WHEN** comic 主题激活且地名标签「东坡塬」位于浅棕绿色块上方
- **THEN** 标签文字周围有半透明白色光晕，文字清晰可读

## MODIFIED Requirements

### Requirement: 漫画主题按 Scale 激活

系统 SHALL 在 tactical scale 级别激活绍宋漫画视觉主题，battle/strategic 级别使用对应的视觉配置。

主题切换 MUST：
- 在管道返回 scale 结果后自动判断并应用
- Tactical 级应用完整的 Canvas 漫画风绘制参数（兵牌、箭头、地形）
- Battle/strategic 级使用简化的 Canvas 绘制参数（更小、更稀疏）
- 用户编辑后重新渲染时重新判断 scale 并切换主题
- 主题配置从 CSS 变量扩展为 JavaScript 配置对象，供 Canvas 渲染器读取

#### Scenario: Tactical 级战役激活漫画主题

- **WHEN** 管道返回 scale 为 `tactical`
- **THEN** Canvas 渲染器加载漫画风完整参数（兵牌 84×56px、箭头 14px、地形完整渲染）

#### Scenario: Battle 级战役使用简化渲染

- **WHEN** 管道返回 scale 为 `battle`
- **THEN** Canvas 渲染器使用简化参数（兵牌 42×28px、箭头 7px、地形简化）

### Requirement: 阵营色系统

系统 SHALL 定义阵营色配置对象，供 Canvas 渲染器和 MapLibre layer 统一引用。

阵营色映射 MUST：
- 宋军：靛蓝 `#2b4c7e`
- 金军：朱砂红 `#c23b22`
- 未知/其他：墨色 `#2c2c2c`
- 交战覆盖：亮红 `#e63946`
- 配置以 JavaScript 对象导出（保留 CSS 变量作为 MapLibre paint 属性引用）

#### Scenario: Canvas 和 MapLibre 使用相同阵营色

- **WHEN** comic 主题激活且部队阵营为金军
- **THEN** Canvas 兵牌边框和 MapLibre 路线颜色都使用 `#c23b22`

### Requirement: Tactical 级宋体标注

系统 SHALL 在 comic 主题下将地图所有文字标签字体切换为宋体系列。

字体堆栈 MUST：`"SimSun", "Songti SC", "Noto Serif SC", serif`

此变更 MUST 涵盖 Canvas 兵牌文字、MapLibre 地名标签、popup 文字。

#### Scenario: Tactical 地图使用宋体

- **WHEN** comic 主题激活
- **THEN** Canvas 兵牌的 `font` 属性使用 Noto Serif SC，MapLibre `text-font` 使用相同字体族

### Requirement: 地名标签半透明白底

系统 SHALL 在 comic 主题下为地名标签添加半透明白色光晕，防止 Canvas 地形色块干扰文字可读性。

标签光晕 MUST：
- MapLibre `text-halo-color`: `rgba(255,255,255,0.75)`
- MapLibre `text-halo-width`: 2.5px
- MapLibre `text-halo-blur`: 0.5px

#### Scenario: 地名标签在地形色块上可读

- **WHEN** comic 主题激活且地名标签「东坡塬」位于 Canvas 地形色块上方
- **THEN** 标签文字周围有半透明白色光晕，文字清晰可读

## REMOVED Requirements

### Requirement: 地形色块渲染

**Reason**: MapLibre `fill` layer 地形色块（通过 GeoJSON source + circle/fill layer 实现半透明圆形）被 Canvas 地形渲染器替代，后者可绘制披麻皴、晕滃线等更丰富的古风地形。

**Migration**: 地形数据通过 LLM 地形推理模块获取，渲染从 MapLibre fill layer 迁移到 Canvas `terrainRenderer.js`。删除前端 `terrain-blocks` GeoJSON source 及对应的 fill layer 构建代码。

### Requirement: 红色印章装饰

**Reason**: DOM div + CSS 实现的 `position: absolute` 印章无法跟随地图内容移动（缩放/平移时固定在屏幕右下角，而非地理参考位置）。Canvas 可直接在地图坐标空间绘制印章，跟随地图内容移动。

**Migration**: 印章从 DOM div 迁移到 Canvas 绘制。删除印章 DOM 元素、CSS 样式及 `updateSeal()` 函数。
