## ADDED Requirements

### Requirement: 数据驱动视口投影

系统 SHALL 在 Tactical 级根据所有数据点的经纬度包围盒计算 Canvas 像素投影，而非依赖 MapLibre 的 `map.project()`。

投影计算 MUST：
- 收集所有 GeoJSON 数据的 (lng, lat) 坐标：地名 features + 部队 banner features + 方向目标 + 路线端点
- 计算 min/max lng 和 min/max lat 包围盒
- 经度跨度修正纬度余弦：`dx = Δlng × 111320 × cos(midLatRad)`
- 纬度跨度：`dy = Δlat × 111320`
- 等比缩放：`scale = min(canvasW / dx, canvasH / dy)`，居中显示
- 最终投影：`x = (lng - minLng) × mPerDegLng × scale + offsetX`，`y = (maxLat - lat) × mPerDegLat × scale + offsetY`

若包围盒跨度为 0或小于 0.001°，MUST 赋予默认 ±0.005° 范围兜底。

#### Scenario: 多点正常投影

- **WHEN** Tactical 级数据包含 3 个地名（坐标各不同）和 1 个部队
- **THEN** 所有投影点落在 Canvas 的 `[padding, W-padding] × [padding, H-padding]` 区域内

#### Scenario: 单点兜底

- **WHEN** 所有数据点坐标完全相同（跨度 < 0.001°）
- **THEN** 系统赋予默认 ±0.005° 范围，地图正常居中渲染

### Requirement: 单 Canvas 渲染

系统 SHALL 在 Tactical 级以单个 Canvas 元素完成所有视觉要素绘制，绘制顺序固定。

绘制顺序 MUST：
1. 背景宣纸色填充（`#f2e8d5`）
2. 地形装饰（预留接口，TODO）
3. 行军路线（线段）
4. 地名标记（城池△、营寨○、标签文字）
5. 部队旗帜（SVG 图标 + 部队名称标签）
6. 攻击箭头（燕尾式 roughjs 手绘箭头）
7. 图例

Canvas MUST 支持 DPR：`canvas.width = cssW × dpr`，`canvas.height = cssH × dpr`，`ctx.scale(dpr, dpr)`。

#### Scenario: Tactical 数据触发单 Canvas 渲染

- **WHEN** SSE 返回 scale 为 `tactical`
- **THEN** 单 Canvas 覆盖 `.map-wrap` 区域，按固定顺序完成全部渲染，无 MapLibre 参与

#### Scenario: 高分屏清晰渲染

- **WHEN** 设备 DPR = 2
- **THEN** Canvas 物理像素为 CSS 尺寸的 2 倍，文字和图标清晰不模糊

### Requirement: 时间轴过滤

系统 SHALL 支持按时间步过滤部队和路线的显示。

`setTimeline(step, total)` MUST：
- 只绘制 `properties.step === step` 的部队旗帜和箭头
- 静态元素（背景、地名）不重新绘制（缓存到离屏 Canvas，TODO）

#### Scenario: 时间轴切换过滤部队

- **WHEN** 时间轴切换到第 2 步
- **THEN** 仅显示 step=2 的部队和箭头，step=1 或 step=3 的部队隐藏

### Requirement: 多点环形分布

系统 SHALL 对同坐标的多个部队按环形分布渲染，避免图标重叠。

环形分布 MUST：
- 读取 `properties._slot` 序号
- 同坐标部队数 N，第 i 个部队偏移：`angle = 2π × i / N`，`offsetX = 30 × cos(angle)`，`offsetY = 30 × sin(angle)`
- 偏移后坐标仍在 padding 保护区内

#### Scenario: 两部队同坐标

- **WHEN** 两支部队驻扎在同一地名坐标
- **THEN** 旗帜分别偏移到该点左右两侧各 30px，不重叠

#### Scenario: 单部队不偏移

- **WHEN** 该坐标只有 1 支部队
- **THEN** 旗帜绘制在原始坐标位置，不偏移

### Requirement: Resize 响应

系统 SHALL 在窗口大小变化时重新计算投影并重绘。

Resize 回调 MUST：
- 重新读取容器 CSS 尺寸，更新 Canvas 物理宽高
- 重算包围盒和投影参数
- 全量重绘

#### Scenario: 窗口大小改变

- **WHEN** 浏览器窗口 resize 导致 `.map-wrap` 尺寸变化
- **THEN** Canvas 物理尺寸更新，投影重算，内容按新尺寸正确重绘

### Requirement: Scale 分叉路由

系统 SHALL 在 SSE 结果处理中按 scale 字段路由到正确的渲染器。

分叉逻辑 MUST：
- `scale === 'tactical'`：调用 `TacticalRenderer.setData(data)`
- 其他 scale：调用现有 `updateMap(data)` 路径
- 用户编辑后重新渲染（`/api/v1/render`）也遵循同样路由

#### Scenario: Tactical 走新路径

- **WHEN** SSE 返回 `scale: 'tactical'`
- **THEN** 不初始化 MapLibre 相关层，直接调用 TacticalRenderer

#### Scenario: Battle 走旧路径

- **WHEN** SSE 返回 `scale: 'battle'`
- **THEN** 调用现有 `updateMap(data)`，MapLibre + 三层 Canvas 正常渲染

### Requirement: 燕尾箭头绘制

系统 SHALL 在 Tactical 级以 roughjs 手绘风格绘制燕尾分叉箭头。

箭头几何 MUST：
- 箭身：从起点到终点的一线段（roughjs linearPath）
- 燕尾分叉：从终点向后张开两条短线（roughjs line）
- 分叉长度 = 线宽 × 4
- 分叉张开角 = 36°（π/5）

#### Scenario: 部队指向目标

- **WHEN** 部队有 `direction_target` 属性且目标在该部队坐标的投影区域内
- **THEN** 绘制燕尾箭头，箭身直达终点，分叉从终点向后张开

### Requirement: 旗帜图标绘制

系统 SHALL 在 Tactical 级绘制部队旗帜 SVG 图标和名称标签。

旗帜绘制 MUST：
- 阵营判断：宋军用 banner-song.svg，金军用 banner-jin.svg，未知用 banner-jin.svg
- 图标尺寸：80px（Tactical 级）
- 名称标签在图标下方 4px 处，字体 bold 13px 宋体

#### Scenario: 宋军部队旗帜

- **WHEN** 部队 faction 包含「宋」
- **THEN** 绘制蓝色宋军旗帜 SVG 图标 + 部队名称标签
