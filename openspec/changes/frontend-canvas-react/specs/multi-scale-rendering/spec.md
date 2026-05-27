# Multi-Scale Rendering 多尺度渲染

## Purpose

根据地图 zoom 级别自动切换渲染策略：小尺度（攻城/战术）Canvas 全控 + 纯色背景，大尺度（战役/会战）MapLibre 瓦片底图 + Canvas 叠加。确保古战场信息在任意缩放级别下清晰可读。

## ADDED Requirements

### Requirement: 四级尺度分类

系统 SHALL 根据 `map.getZoom()` 将渲染分为四个尺度级别，每级使用不同策略。

级别定义 MUST：
- **攻城 (siege)**：zoom ≥ 16，Canvas 全控，纯色 `#f5f0e1` 背景，渲染城墙/城门/街巷/攻守双方
- **战术 (tactical)**：14 ≤ zoom ≤ 15，Canvas 为主，纯色背景 + 示意地形，渲染兵牌/箭头/地形色块
- **战役 (battle)**：10 ≤ zoom ≤ 13，MapLibre 瓦片底图 + Canvas 叠加，渲染部队/战略箭头/古风标注
- **会战 (strategic)**：zoom ≤ 9，MapLibre 瓦片底图为主 + Canvas 叠加兵团标注/战区箭头/印章

#### Scenario: 用户缩放到战术级

- **WHEN** 用户将地图 zoom 从 12 放大到 14
- **THEN** 底图从 OpenFreeMap 瓦片切换为纯色 `#f5f0e1`，Canvas 地形细节增强

#### Scenario: 用户缩放到战役级

- **WHEN** 用户将地图 zoom 从 14 缩小到 11
- **THEN** 底图从纯色切换为 OpenFreeMap 瓦片，Canvas 古风标注叠加在瓦片之上

### Requirement: 底图源动态切换

系统 SHALL 根据当前尺度级别自动切换 MapLibre 的 style/底图源，无缝过渡。

切换规则 MUST：
- Siege / Tactical：使用纯色 background style（无外部瓦片请求）
- Battle / Strategic：使用 OpenFreeMap 矢量瓦片 style
- 切换时使用 MapLibre `setStyle()` 或预加载两个 style 实例
- 切换阈值 ±0.5 zoom 的滞回带，避免频繁切换

#### Scenario: 跨阈值时的滞回

- **WHEN** 用户在 zoom 13.5 附近反复缩放
- **THEN** 底图不会每帧切换，仅在稳定在阈值一侧 0.5 zoom 后才切换

### Requirement: 尺度自适应部队渲染

系统 SHALL 根据尺度级别调整部队兵牌和箭头的渲染细节。

细节级别 MUST：
- Siege/Tactical (zoom ≥ 14)：完整兵牌卡片（84×56px）+ 粗壮箭头（14px）+ 部队全名
- Battle (zoom 10-13)：简化兵牌（42×28px）+ 标准箭头（7px）+ 部队简称
- Strategic (zoom ≤ 9)：最小化标记（圆点 + 编号）+ 细线箭头（3px）+ 仅显示阵营色

#### Scenario: 战略级部队缩略

- **WHEN** 地图 zoom 为 7
- **THEN** 每个部队渲染为阵营色圆点（r=6px）+ 编号标签，不渲染完整兵牌卡片

### Requirement: 尺度自适应路线渲染

系统 SHALL 根据尺度级别调整行军路线的视觉样式。

路线样式 MUST：
- Siege/Tactical (zoom ≥ 14)：粗实线（3.5px）+ 箭头 + 端点锚点
- Battle (zoom 10-13)：虚线 `[6, 3]`（2px）+ 箭头
- Strategic (zoom ≤ 9)：细虚线 `[4, 4]`（1.5px），无锚点

#### Scenario: 放大后路线变粗

- **WHEN** 用户从 zoom 9 放大到 zoom 14
- **THEN** 行军路线从细虚线平滑过渡为粗实线

### Requirement: 尺度自适应地名标签

系统 SHALL 根据尺度级别调整地名标签的显示密度和字号。

标签规则 MUST：
- Siege/Tactical (zoom ≥ 14)：显示所有地名 + 古今对照标签，字号 15px
- Battle (zoom 10-13)：显示重要地名，字号 12px，collision-box 收紧避免重叠
- Strategic (zoom ≤ 9)：仅显示城市/关隘级别地名，字号 10px，古今对照隐藏

#### Scenario: 缩小后隐藏细节标签

- **WHEN** 用户将地图从 zoom 14 缩小到 zoom 8
- **THEN** 小地名标签（如「塬东小路」）隐藏，仅保留主要地名（如「蔡州」）
