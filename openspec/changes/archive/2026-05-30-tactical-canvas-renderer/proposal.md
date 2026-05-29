## Why

Tactical 级当前使用 MapLibre + 三层 Canvas 架构，MapLibre 视口独立于数据范围，导致部队坐标可能投影到 Canvas 画布之外，箭头被裁剪。Tactical 级范围仅几十公里且不支持缩放平移，不需要地图引擎。改为纯 Canvas 架构，由数据包围盒决定视口，从根源消除坐标不一致。

## What Changes

- 新增 `tacticalRenderer.js`：Tactical 级专用单 Canvas 渲染器，自包含投影计算和渲染逻辑
- 修改 `app.js`：SSE result 处理中按 scale 分叉，tactical 走新路径，其他 scale 保持现有路径
- 修改 `index.html`：引入 `tacticalRenderer.js`

## Capabilities

### New Capabilities
- `tactical-canvas-renderer`: Tactical 级纯 Canvas 渲染，包括经纬度线性投影、数据驱动视口、单层绘制（背景→地形→路线→地名→旗帜→箭头→标签）

### Modified Capabilities
- `comic-style-tactical-theme`: Tactical 级不再使用 MapLibre，相关的地形色块、印章、标签渲染从 MapLibre layer 体系迁移到 Canvas 绘制

## Impact

- 新增文件：`static/js/tacticalRenderer.js`（~250 行）
- 修改文件：`static/js/app.js`（~5 行分叉逻辑）、`static/index.html`（1 行 script 引用）
- 不动文件：`map.js`、`canvasRenderer.js`、`terrainRenderer.js`（战役/战略级保留）
- 依赖：roughjs（已有）、旗帜 SVG 图标（已有）
- 去掉的依赖：Tactical 级不再依赖 MapLibre 的 `map.project()` 和 `fitBounds()`
