# Canvas Unit Renderer 部队兵牌渲染

## Purpose

Canvas 2D 覆盖层替代 MapLibre symbol layer 渲染部队兵牌和进攻箭头，实现像素偏移自由控制、碰撞避让和绍宋漫画风格。

## ADDED Requirements

### Requirement: Canvas 覆盖层初始化

系统 SHALL 在 MapLibre 地图容器上创建一个透明 Canvas 覆盖层，尺寸与地图容器完全一致，pointer-events 为 none（交互穿透到地图）。

Canvas MUST：
- position 为 absolute，top/left 为 0，width/height 与 MapLibre 容器同步
- z-index 高于 MapLibre canvas 但低于 MapLibre popup/controls
- 监听 MapLibre `resize` 事件自动更新 Canvas 尺寸
- pointer-events 为 none，所有点击穿透到 MapLibre

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

### Requirement: 兵牌卡片渲染

系统 SHALL 以绍宋漫画风格绘制部队兵牌：圆角矩形卡片 + 双层边框 + 顶部阵营色条 + 部队名称 + Canvas dropShadow 阴影。

兵牌视觉参数 MUST：
- 默认宽度 84px（文字自适应 + padding），高度 56px
- 圆角半径 12px
- 外边框 3px 阵营色，内边框 1px 墨色 `#2c2c2c`（双层浮雕效果）
- 顶部 12px 高阵营色色条
- Canvas `dropShadow(2px, 3px, 4px, rgba(0,0,0,0.25))` 阴影
- 填充色：卡片主体宣纸色 `#faf6ed`
- 字体：14px 'Noto Serif SC', 'Ma Shan Zheng', serif，墨色 `#2c2c2c`
- 文本居中，单行，超出宽度时缩小字号

#### Scenario: 宋军兵牌渲染

- **WHEN** 部队「焦文通部」阵营为宋军
- **THEN** 兵牌外边框和色条为靛蓝 `#2b4c7e`，文字显示「焦文通部」

#### Scenario: 金军兵牌渲染

- **WHEN** 部队「合扎猛安」阵营为金军
- **THEN** 兵牌外边框和色条为朱砂红 `#c23b22`

#### Scenario: 未知阵营兵牌渲染

- **WHEN** 部队阵营为 unknown 或 null
- **THEN** 兵牌外边框和色条为墨色 `#2c2c2c`

### Requirement: 进攻箭头渲染

系统 SHALL 从部队兵牌位置出发，沿进攻方向绘制带微弧的粗壮箭头，体现绍宋漫画的毛笔笔触风格。

箭头参数 MUST：
- 线宽 14px（卡片宽的 1/5）
- 头部宽高比 3:2（近等边三角形）
- 箭头描边 1.5px 黑色
- 路径使用二次贝塞尔曲线（微弧），控制点沿方向角偏移
- 颜色跟随阵营色
- 箭头长度 = 数据包围盒对角线 × scale 系数（tactical 20% / battle 8% / strategic 3%）

#### Scenario: 宋军进攻箭头

- **WHEN** 部队「焦文通部」有 direction 值且阵营为宋军
- **THEN** 从兵牌位置沿方向角绘制靛蓝色粗箭头，黑色描边，微弧路径

#### Scenario: 无方向部队不绘制箭头

- **WHEN** 部队无 direction 字段或 direction 为 null
- **THEN** 仅渲染兵牌卡片，不绘制箭头

#### Scenario: 交战状态箭头加粗

- **WHEN** 部队状态为 engaging
- **THEN** 箭头线宽增至 18px，描边增至 2px，颜色使用亮红 `#e63946`

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
- **交战** (engaging)：兵牌边框颜色渐变为亮红 + 脉冲效果（3 次，每次 200ms）
- **崩溃** (routing)：兵牌 opacity 在 3 个步骤内从 1.0 递减到 0，箭头碎裂为散点

#### Scenario: 部队首次出现生长动画

- **WHEN** 时间线推进到步骤 4，合扎猛安首次出现且状态为 advancing
- **THEN** 箭头从兵牌位置生长（600ms），同时兵牌 opacity 从 0 渐变到 1

#### Scenario: 溃散部队碎裂消失

- **WHEN** 焦文通部状态变为 routing 后推进 3 个步骤
- **THEN** 兵牌 opacity 递减至 0，箭头碎裂为 8 个随机散点淡出
