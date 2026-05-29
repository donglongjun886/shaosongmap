## MODIFIED Requirements

### Requirement: 漫画主题按 Scale 激活

系统 SHALL 在 tactical scale 级别激活绍宋漫画视觉主题，battle/strategic 级别使用对应的视觉配置。

主题切换 MUST：
- 在管道返回 scale 结果后自动判断并应用
- Tactical 级应用完整 Canvas 漫画风绘制参数（兵牌、箭头），无需 MapLibre
- Tactical 级使用 TacticalRenderer（纯 Canvas）渲染全部要素
- Battle/strategic 级继续使用 MapLibre + 三层 Canvas 架构
- 用户编辑后重新渲染时重新判断 scale 并切换渲染器

#### Scenario: Tactical 级战役激活漫画主题

- **WHEN** 管道返回 scale 为 `tactical`
- **THEN** TacticalRenderer 接管渲染，Canvas 加载漫画风完整参数（兵牌 80px、箭头线宽 6、字体 13px）

#### Scenario: Battle 级战役使用 MapLibre 渲染

- **WHEN** 管道返回 scale 为 `battle`
- **THEN** 调用现有 `updateMap(data)` 路径，MapLibre + 三层 Canvas 正常渲染

### Requirement: 阵营色系统

系统 SHALL 在 Tactical 级 Canvas 渲染中使用阵营色 JavaScript 配置对象驱动着色。

阵营色映射 MUST：
- 宋军：靛蓝 `#2b4c7e`
- 金军：朱砂红 `#8b4513`
- 未知/其他：墨色 `#2c2c2c`
- 配置在 TacticalRenderer 内部定义，不依赖 CSS 变量

#### Scenario: Canvas 旗杆和箭头使用阵营色

- **WHEN** 部队阵营为金军
- **THEN** Canvas 绘制的旗帜色条和攻击箭头均使用 `#8b4513`

### Requirement: Tactical 级宋体标注

系统 SHALL 在 Tactical 级 Canvas 渲染中使用宋体系列字体。

字体堆栈 MUST：`"Noto Serif SC", "SimSun", serif`

此变更 MUST 涵盖 Canvas 兵牌文字和地名标签。

#### Scenario: Tactical 地图使用宋体

- **WHEN** TacticalRenderer 绘制部队名称标签
- **THEN** `ctx.font` 使用 `bold 13px "Noto Serif SC", "SimSun", serif`

## REMOVED Requirements

### Requirement: 地形色块渲染

**Reason**: Tactical 级不再使用 MapLibre fill layer 渲染地形色块。地形渲染迁移到 Canvas，实现方式待后续设计。

**Migration**: 删除 Tactical 级中 MapLibre terrain-blocks fill layer 的构建代码。Canvas 地形渲染保留接口（TODO），当前版本不实现。

### Requirement: 红色印章装饰

**Reason**: Tactical 级不再使用 DOM div + CSS 的印章实现。印章待后续由 Canvas 直接绘制。

**Migration**: Tactical 级渲染时不显示印章。DOM 印章元素保留给 battle/strategic 级使用。

### Requirement: 地名标签半透明白底

**Reason**: Tactical 级不再使用 MapLibre text-halo 实现标签背景。待后续由 Canvas 实现。

**Migration**: Tactical 级地名标签当前直接绘制文字，不加光晕。Battle/strategic 级保持 MapLibre text-halo 不变。
