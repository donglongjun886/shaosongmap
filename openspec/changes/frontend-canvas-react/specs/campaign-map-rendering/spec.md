# Campaign Map Rendering 战役地图渲染 (Delta)

## ADDED Requirements

### Requirement: Canvas 覆盖层架构

系统 SHALL 在 MapLibre 地图容器上叠加 Canvas 2D 覆盖层，用于渲染部队兵牌、进攻箭头、地形色块和古风标注。

Canvas 覆盖层 MUST：
- 与 MapLibre 容器完全重叠，position absolute，pointer-events none
- 通过 `map.project()` 将地理坐标转为像素坐标
- 在 `requestAnimationFrame` 循环中绘制，跟随地图 move/zoom 自动更新
- z-index 层级：底图 < Canvas 地形 < MapLibre 路线 < Canvas 兵牌 < MapLibre 地名标记

#### Scenario: Canvas 与 MapLibre 同步

- **WHEN** 用户拖拽平移地图
- **THEN** Canvas 上的兵牌和箭头在下一帧跟随地理坐标移动到正确位置

#### Scenario: Canvas 不拦截地图交互

- **WHEN** 用户点击 Canvas 覆盖的兵牌位置
- **THEN** 点击穿透到 MapLibre，触发地名 popup

### Requirement: 多尺度底图策略

系统 SHALL 根据 map zoom 自动选择底图策略。

底图规则 MUST：
- zoom ≥ 14 (siege/tactical)：纯色 `#f5f0e1` 背景，不加载外部瓦片
- zoom < 14 (battle/strategic)：OpenFreeMap 矢量瓦片，提供地形和地名参照
- 切换阈值有 ±0.5 zoom 滞回带，避免频繁切换

#### Scenario: 战术级纯色背景

- **WHEN** 地图 zoom 为 15
- **THEN** MapLibre 使用纯色 background style，无外部瓦片请求

#### Scenario: 战役级瓦片底图

- **WHEN** 地图 zoom 为 11
- **THEN** MapLibre 加载 OpenFreeMap 矢量瓦片，Canvas 兵牌和箭头叠加在瓦片之上

## MODIFIED Requirements

### Requirement: 交互式地图渲染

系统 SHALL 使用 MapLibre GL JS 渲染交互式底图（纯色背景或矢量瓦片），Canvas 2D 覆盖层渲染所有古风战斗元素（部队兵牌、进攻箭头、地形色块）。

地图 MUST 支持：
- 鼠标缩放（+/-）和拖拽平移
- 按 `source` 字段区分地名标记样式（实心=CHGIS，空心=LLM 推断）——**保留在 MapLibre symbol layer**
- 地名标记使用 zoom 表达式动态调整 circle-radius 和 text-size——**保留在 MapLibre symbol layer**
- 古今地名对照双标签层——**保留在 MapLibre symbol layer**
- 行军路线以带箭头线条展示——**保留在 MapLibre line layer**
- 部队以 Canvas 兵牌 + 进攻箭头展示——**改为 Canvas 2D，删除 MapLibre unit-banners/comic-unit-icons source**
- 部队箭头在 timeline 模式下根据当前 step 动态更新——**Canvas rAF 循环每帧检查**
- 多个部队关联同一地名时，Canvas 像素空间错位排列——**像素偏移替代地理偏移**
- 部队箭头图层可见性切换——**通过 Canvas dirty flag 控制**
- 地形色块通过 Canvas 绘制——**替代 MapLibre fill layer 地形色块**

地图在三种页面状态下 MUST 保持现有初始化行为不变（引导态/结果态/编辑态）。

#### Scenario: 地图加载战役数据

- **WHEN** 后端返回包含 GeoJSON 的战役数据
- **THEN** MapLibre 渲染地名标记和路线，Canvas 渲染部队兵牌和箭头

#### Scenario: 地图不依赖外部瓦片服务（战术级）

- **WHEN** scale 为 tactical 且 zoom ≥ 14
- **THEN** 地图渲染纯色背景 `#f5f0e1`，不发起任何外部瓦片网络请求

## REMOVED Requirements

### Requirement: Comic 主题地形色块图层

**Reason**: MapLibre `fill` layer 地形色块（通过 GeoJSON source + circle/fill layer 实现）被 Canvas 地形渲染器替代。Canvas 可以绘制披麻皴、晕滃线等古风地形，表现力远超半透明圆形色块。

**Migration**: 地形数据仍从 LLM 提取，但渲染路径从前端 MapLibre fill layer 改为 Canvas 2D `terrainRenderer.js`。删除 `terrain-blocks` GeoJSON source 和对应的 fill layer 代码。

### Requirement: Comic 主题箭头加粗与笔触感

**Reason**: MapLibre line layer 的 `line-cap: round` + `line-width` 方案表达力有限，无法实现微弧贝塞尔路径、变宽箭头、毛笔笔触效果。Canvas 2D 原生支持这些绘制。

**Migration**: 箭头渲染全部迁移到 Canvas。MapLibre line layer 仅保留行军路线（route-lines），删除 comic 主题特有的 line paint 覆盖逻辑。

### Requirement: Comic 主题印章叠加层

**Reason**: 印章作为古风视觉元素，跟随地图缩放平移时应保持固定的地理参考位置。DOM div + CSS 实现的印章（`position: absolute`）无法跟随地图内容移动。Canvas 可以直接在数据坐标对应位置绘制印章。

**Migration**: 印章从 DOM div 迁移到 Canvas 绘制，位置由 `map.project()` 动态计算。删除印章 DOM 元素及 CSS。
