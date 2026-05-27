# Comic Style Tactical Theme 漫画战术主题 (Delta)

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
