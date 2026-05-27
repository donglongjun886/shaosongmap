# Canvas Terrain Renderer 地形示意渲染

## Purpose

LLM 从战役文本推断地形特征（塬/坡/谷/河流），Canvas 2D 程序化生成示意地形，替代精确 DEM 方案。渲染为中国古代地图风格（披麻皴、晕滃线、双线河流）。

## ADDED Requirements

### Requirement: LLM 地形特征提取

系统 SHALL 在战役文本提取管道中新增地形特征分析，从文本中识别地形关键词并输出结构化地形数据。

地形类型 MUST 包括：
- `plateau` (塬)：高台地形，有陡峭边缘
- `slope` (坡)：缓坡或陡坡，有方向性
- `gully` (河沟)：干涸或季节性河沟，有路径
- `valley` (谷)：两山之间的谷地
- `mountain_pass` (隘口)：山口/关隘
- `flat` (平原)：开阔平坦地形

每个地形特征 MUST 包含：
- `type`：地形类型
- `name`：地形名称（从文本提取）
- `center`：经纬度坐标（关联到最近的地名坐标或 LLM 推断）
- `radius_km`：影响半径（默认值按类型分档）
- `direction`：方向角（坡、谷等有方向性的地形）

#### Scenario: 黄土塬地形提取

- **WHEN** 输入文本包含「东坡塬北侧列阵」「自塬东小路」「塬底直冲」
- **THEN** LLM 提取 `{type: "plateau", name: "东坡塬", radius_km: 2}` 和 `{type: "slope", name: "塬底", direction: "S"}`

#### Scenario: 河沟地形提取

- **WHEN** 输入文本包含「沿干涸河沟隐蔽南下」
- **THEN** LLM 提取 `{type: "gully", name: "干涸河沟", direction: "S"}`

### Requirement: 地形 Canvas 渲染

系统 SHALL 在 Canvas 覆盖层上以古代地图风格绘制示意地形，渲染在部队兵牌和箭头之下。

地形渲染风格 MUST：
- 塬 (plateau)：浅棕绿 `rgba(139,119,101,0.15)` 圆角矩形填充 + 边缘密集短竖线（披麻皴风格，`#8b766b`，opacity 0.3）
- 坡 (slope)：渐变填充（从地形色到透明）+ 稀疏短竖线（间距 8px）
- 河沟 (gully)：蓝色 `rgba(100,149,237,0.4)` 虚线曲线（`[8, 4]` dash），线宽 2px
- 谷 (valley)：浅黄 `rgba(218,195,125,0.12)` V 形填充
- 隘口 (mountain_pass)：双线收窄标记

#### Scenario: 东坡塬渲染为披麻皴方块

- **WHEN** 地形数据包含 type=plateau 的「东坡塬」
- **THEN** Canvas 上以东坡塬为中心绘制浅棕绿圆角矩形，边缘有密集短竖线模拟山体

#### Scenario: 干涸河沟渲染为蓝色虚线

- **WHEN** 地形数据包含 type=gully 的「干涸河沟」
- **THEN** Canvas 上绘制蓝色虚线曲线

### Requirement: 地形缩放自适应

系统 SHALL 根据地图 zoom 级别调整地形渲染的视觉密度和尺寸。

缩放规则 MUST：
- Zoom ≥ 14 (tactical)：完整渲染，短竖线密集（间距 4px），色块填充 opacity 正常
- Zoom 10-13 (battle)：简化渲染，短竖线稀疏（间距 12px），色块填充 opacity 减半
- Zoom ≤ 9 (strategic)：仅渲染色块填充（无短竖线），opacity 减至 1/3

#### Scenario: 战术级完整地形

- **WHEN** 地图 zoom 为 14
- **THEN** 地形色块和披麻皴线条完整渲染

#### Scenario: 战略级简化地形

- **WHEN** 地图 zoom 为 7
- **THEN** 仅显示浅色地形色块，无短竖线细节

### Requirement: 地形与地图数据层级关系

系统 SHALL 确保地形色块渲染在正确 z-index 层级：底图 < 地形色块 < 行军路线 < 兵牌 < 地名标记。

#### Scenario: 路线浮在地形之上

- **WHEN** 行军路线穿过「东坡塬」地形色块
- **THEN** 路线线条始终渲染在色块上方，不被遮挡

#### Scenario: 兵牌浮在地形之上

- **WHEN** 部队兵牌位于「塬底」地形区域
- **THEN** 兵牌卡片和箭头渲染在色块上方，清晰可见
