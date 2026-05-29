## Context

Tactical 级当前复用战役级的 MapLibre + 三层 Canvas（terrain/route/unit）架构。MapLibre 视口由 `fitBounds` 根据地点坐标计算，但部队坐标可能落在视口外——Canvas 高度 600px 时部队投到 Y=797，箭头被画布边界裁剪。

Tactical 级特点：范围几十公里，不支持缩放/平移，地图尺寸在 LLM 提取后固定。不需要地图引擎的投影和交互能力。

## Goals / Non-Goals

**Goals:**
- Tactical 级改为单 Canvas 渲染，去掉 MapLibre 依赖（仅 Tactical 级）
- 视口由数据包围盒决定，所有元素天然在画布内，消除坐标不一致
- 支持 DPR、环形分布、resize 重算

**Non-Goals:**
- Battle/Strategic 级保持不变，继续使用 MapLibre
- 不抽取公共 renderUtils.js（TODO 备注）
- 不做最小地理跨度限制
- 不改动后端 API

## Decisions

### 1. 单 Canvas vs 保持多层
**选择**：单 Canvas，按固定顺序绘制（背景→地形→路线→地名→旗帜→箭头→标签）

**理由**：数据驱动视口保证所有元素在画布内，不需要分层管理。Tactical 级数据量小（几个地点+部队），全量重绘 < 5ms。

### 2. 线性投影 vs Mercator 投影
**选择**：经纬度直接线性映射到 Canvas 像素

**理由**：几十公里范围内经线近似平行，球面曲率可忽略。公式：`x = (lng - minLng) × mPerDegLng × scale`，`y = (maxLat - lat) × mPerDegLat × scale`。

### 3. 视口计算：数据驱动
**选择**：收集所有 GeojSON 数据点的 (lng, lat)，算包围盒，等比缩放 + padding 居中

**理由**：数据范围决定视口，所有投影点天然在 `[padding, W-padding] × [padding, H-padding]` 内，不存在超出画布的可能。

### 4. DPR 支持
**选择**：`canvas.width = cssW × dpr`，`ctx.scale(dpr, dpr)`，`dpr = Math.min(devicePixelRatio, 2)`

**理由**：防止 Retina 屏文字和图标发虚，和现有 canvasRenderer.js 一致。

### 5. 多点环形分布
**选择**：同坐标 N 个部队以该点为中心、半径 30px 均匀分布。`angle_i = 2π × _slot / N`

**理由**：后端已打 `_slot` 序号，前端直接按顺序围成圈。比固定偏移 20px 更合理，不会重叠。

### 6. 代码组织：独立文件，暂不抽取公共模块
**选择**：`_drawArrow`、`_drawFlag` 等从 canvasRenderer.js 复制到 tacticalRenderer.js，暂不抽取 renderUtils.js

**理由**：先独立验证 Tactical 路径，后续 Battle/Strategic 改造时统一抽取。复制处加 TODO 注释。

## Risks / Trade-offs

| Risk | Mitigation |
|------|-----------|
| 包围盒除零（单点/共线） | 跨度 < 0.001° 时赋予默认 ±0.005° 范围 |
| 和 canvasRenderer.js 代码重复 | 暂接受，TODO 注释标注后续抽 renderUtils.js |
| Resize 重算投影不做防抖 | Tactical 无交互缩放，窗口 resize 频率低，不做防抖无影响 |
| 环形分布的部队偏移后可能越界 | 偏移量 30px < padding（通常 60-80px），不会越界 |
