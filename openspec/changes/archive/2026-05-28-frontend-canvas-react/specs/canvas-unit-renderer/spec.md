# Canvas Unit Renderer 部队兵牌渲染

## Purpose

Canvas 2D 三层覆盖层（terrainCanvas / routeCanvas / unitCanvas）替代 MapLibre symbol layer 渲染部队兵牌和进攻箭头。使用 roughjs 生成手绘风格图形（一次性，初始化时），Path2D + 离屏 Canvas 缓存后，在 rAF 渲染循环中使用原生 Canvas API 绘制，实现像素偏移自由控制、碰撞避让和绍宋漫画风格。

## ADDED Requirements

### Requirement: Canvas 覆盖层初始化（三层架构）

系统 SHALL 在 MapLibre 地图容器上创建三个透明 Canvas 覆盖层，按 z-index 分层：

- `terrainCanvas`（z-index: 10）：静态地形色块，仅在 zoom 跨 0.5 档时重绘
- `routeCanvas`（z-index: 20）：路线和地名，仅在时间轴步骤切换时重绘
- `unitCanvas`（z-index: 30）：兵牌和箭头，rAF 持续渲染

Canvas MUST：
- position 为 absolute，top/left 为 0，width/height 与 MapLibre 容器同步
- `width/height` 属性 × `devicePixelRatio`，CSS 尺寸保持逻辑像素
- 所有 Canvas 上下文中 `ctx.scale(dpr, dpr)` 适配 Retina 屏幕
- pointer-events 为 none，所有点击穿透到 MapLibre
- 单 Canvas 最大物理像素限制 4096px，低端设备降级合并 routeCanvas + terrainCanvas
- 监听 MapLibre `resize` 事件自动更新 Canvas 尺寸 + DPR 重算

#### Scenario: Canvas 尺寸跟随地图容器

- **WHEN** 用户缩放浏览器窗口导致地图容器尺寸变化
- **THEN** Canvas 元素的 width/height 属性自动同步为地图容器的新尺寸

#### Scenario: Canvas 不拦截地图交互

- **WHEN** 用户点击 Canvas 覆盖的部队兵牌位置
- **THEN** 点击事件穿透到 MapLibre，触发地名 popup 或地图拖拽

### Requirement: 地理坐标转屏幕像素

系统 SHALL 使用 `map.project([lng, lat])` 将部队地理坐标转换为 Canvas 像素坐标，在每帧渲染前重新计算以跟随地图平移和缩放。

坐标转换 MUST：
- 在 `requestAnimationFrame` 回调中调用 `map.project()`
- 仅绘制屏幕可视范围内的元素（视口裁剪）
- z→y 映射保持地理坐标一致性

#### Scenario: 地图平移时兵牌跟随

- **WHEN** 用户拖拽平移地图
- **THEN** Canvas 上的兵牌在下一帧（~16ms）内跟随地理坐标平移到新位置

#### Scenario: 视口外兵牌不绘制

- **WHEN** 某部队的地理坐标在当前视口之外
- **THEN** Canvas 跳过该部队的绘制，节省渲染开销

### Requirement: 兵牌卡片渲染（roughjs 生成 + 缓存）

系统 SHALL 在初始化时使用 roughjs 生成部队兵牌的 Path2D + 离屏 Canvas，缓存后在 rAF 循环中使用原生 API 绘制。**roughjs 不在 rAF 热路径中实时调用。**

roughjs 生成参数 MUST（统一在 `THEME_CONFIG` 中定义）：
- 卡片尺寸：84px 宽 × 56px 高
- 圆角半径：12px
- roughness：0.8，bowing：0.5
- 外边框：3px 阵营色（宋军 `#2b4c7e` / 金军 `#8b4513` / 未知 `#2c2c2c`）
- 内边框：1px 墨色 `#2c2c2c`（双层浮雕效果）
- 顶部色条：12px 高，阵营色
- 填充色：宣纸色 `#faf6ed`
- 阴影：Canvas `shadowOffsetX: 2, shadowOffsetY: 3, shadowBlur: 4, shadowColor: rgba(0,0,0,0.25)`
- 字体：14px 'Noto Serif SC', 'SimSun', serif，墨色 `#2c2c2c`
- 文本居中，单行，超出宽度时缩小字号

**roughjs 使用模式**：
```
初始化（一次性）：
  roughGen.rectangle(0, 0, 84, 56, params) → Path2D → 缓存到 Map<string, Path2D>
  同时渲染到离屏 Canvas（含色条、文字）→ 缓存为 HTMLCanvasElement

rAF 每帧（热路径）：
  ctx.save()
  ctx.translate(screenX, screenY)  // 位移到屏幕位置
  ctx.drawImage(cachedOffscreen, -42, -28)  // 贴图（零开销）
  ctx.restore()
```

**局部坐标系**：roughjs 生成时使用局部坐标（0, 0 为卡片中心），渲染时 `ctx.translate()` 位移。避免因屏幕坐标变化导致线条蠕动闪烁。

#### Scenario: 宋军兵牌渲染

- **WHEN** 部队「焦文通部」阵营为宋军
- **THEN** 兵牌外边框和色条为靛蓝 `#2b4c7e`，文字显示「焦文通部」

#### Scenario: 金军兵牌渲染

- **WHEN** 部队「合扎猛安」阵营为金军
- **THEN** 兵牌外边框和色条为朱砂红 `#c23b22`

#### Scenario: 未知阵营兵牌渲染

- **WHEN** 部队阵营为 unknown 或 null
- **THEN** 兵牌外边框和色条为墨色 `#2c2c2c`

### Requirement: 进攻箭头渲染（roughjs linearPath + 缓存）

系统 SHALL 在初始化时使用 roughjs 生成进攻箭头的 Path2D，缓存后在 rAF 循环中使用原生 `ctx.stroke(cachedPath)` 绘制。

roughjs 生成参数 MUST：
- 线宽：14px（卡片宽的 1/5）
- 头部宽高比：3:2（近等边三角形，漫画风格）
- 箭头描边：1.5px 黑色 `#2c2c2c`
- 路径：`roughGen.linearPath(points, { bowing: 1.5, roughness: 1.2, strokeWidth: 14 })`
- 微弧贝塞尔：bowing 1.5 产生毛笔笔锋般的自然弯曲
- 颜色：跟随阵营色（宋 `#2b4c7e` / 金 `#8b4513` / 联军 `#5a7a6a`）
- 箭头长度：数据包围盒对角线 × scale 系数（tactical 20% / battle 8% / strategic 3%）
- 固定 seed 保证每帧一致性

**roughjs 使用模式**：
```
初始化（一次性）：
  roughGen.linearPath(localPoints, params) → Path2D → 缓存

rAF 每帧（热路径）：
  ctx.save()
  ctx.translate(screenX, screenY)
  ctx.strokeStyle = factionColor
  ctx.lineWidth = 14
  ctx.stroke(cachedPath)  // 原生 API，极快
  ctx.restore()
```

#### Scenario: 宋军进攻箭头

- **WHEN** 部队「焦文通部」有 direction 值且阵营为宋军
- **THEN** 从兵牌位置沿方向角绘制靛蓝色粗箭头，黑色描边，微弧路径

#### Scenario: 无方向部队不绘制箭头

- **WHEN** 部队无 direction 字段或 direction 为 null
- **THEN** 仅渲染兵牌卡片，不绘制箭头

### Requirement: 同坐标多部队像素偏移

系统 SHALL 在多个部队关联同一地点时，在 Canvas 像素空间沿南北方向错位排列兵牌，确保不重叠。

偏移算法 MUST：
- 同坐标部队按 `_slot` 序号（0, 1, 2...）沿南北方向排列
- 间距 = 卡片高度 56px + 8px 间隙 = 64px
- 以地理坐标为中心对称分布：(slot - (count-1)/2) × 64px
- 偏移是纯像素操作，不修改地理坐标

#### Scenario: 三个部队同地错位

- **WHEN** 「焦文通部」「郦琼部」「王彦中军」都关联到「东坡塬」
- **THEN** 三个兵牌在 Canvas 上以东坡塬的屏幕像素坐标为中心，沿南北各偏移 -64px、0、+64px

#### Scenario: 单部队不偏移

- **WHEN** 仅一个部队关联到某地名
- **THEN** 兵牌以该地名的像素坐标为中心渲染，无偏移

### Requirement: 碰撞避让

系统 SHALL 在 Canvas 渲染前进行简单的碰撞检测，避免兵牌与地名标记重叠。

避让策略 MUST：
- 获取当前视口内所有地名标记的屏幕像素位置
- 兵牌优先渲染在锚点北侧，若与地名标记重叠则向南偏移
- 碰撞检测使用 AABB（轴对齐包围盒）简化计算

#### Scenario: 兵牌与地名重叠时偏移

- **WHEN** 某部队兵牌的默认渲染位置与地名标记「东坡塬」的像素区域重叠
- **THEN** 兵牌自动向南偏移 64px，再检查，最多尝试 3 次

### Requirement: 渲染性能

系统 SHALL 确保 Canvas 渲染在标准硬件上保持 60fps，不影响地图交互流畅度。

性能约束 MUST：
- 使用 `requestAnimationFrame` 驱动渲染循环
- 使用脏标记（dirty flag）跳过无变化的帧
- 仅绘制屏幕可视范围内的元素
- 单帧绘制耗时 < 5ms（10 个兵牌以内）

#### Scenario: 地图静止时零绘制开销

- **WHEN** 地图静止（无 move/zoom/数据更新）
- **THEN** rAF 循环仅执行脏标记检查（< 0.1ms），不触发 Canvas 重绘

#### Scenario: 缩放时流畅渲染

- **WHEN** 用户快速缩放地图
- **THEN** 每帧兵牌重绘耗时 < 5ms，视觉上无抖动或卡顿

### Requirement: 状态动画

系统 SHALL 在部队状态变化时通过 Canvas 实现过渡动画。

动画类型 MUST：
- **进军** (advancing)：箭头从兵牌位置生长动画（600ms，箭尾→箭尖逐步绘制）
- **崩溃** (routing)：兵牌 opacity 在 3 个步骤内从 1.0 递减到 0，箭头碎裂为散点

#### Scenario: 部队首次出现生长动画

- **WHEN** 时间线推进到步骤 4，合扎猛安首次出现且状态为 advancing
- **THEN** 箭头从兵牌位置生长（600ms），同时兵牌 opacity 从 0 渐变到 1

#### Scenario: 溃散部队碎裂消失

- **WHEN** 焦文通部状态变为 routing 后推进 3 个步骤
- **THEN** 兵牌 opacity 递减至 0，箭头碎裂为 8 个随机散点淡出
