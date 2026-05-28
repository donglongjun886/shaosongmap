## Why

MapLibre symbol layer 的同坐标多部队偏移方案（地理坐标偏移）三次补丁仍未根治——低 zoom 时偏移量爆炸（zoom 10 → 14km）。且当前 vanilla JS 手写 Canvas（`_drawWideArrow` 100+ 行、`_makeIconSVG` 30+ 行）代码维护成本高，古风手绘效果（毛笔笔锋、披麻皴、双层浮雕边框）受限。需要引入 roughjs 手绘渲染引擎 + 三层 Canvas 架构，从底层重构视觉表现。

## What Changes

- **新增** roughjs（~10KB）手绘风格渲染引擎，替代手写 Canvas 贝塞尔抖动和竖线循环
- **新增** 三层 Canvas 架构（terrainCanvas / routeCanvas / unitCanvas），按重绘频率分层
- **新增** Canvas 古风地形渲染（roughjs hachure 参数梯度表达海拔高度差异："墨分五色"）
- **新增** THEME_CONFIG 配置对象：统一管理阵营色、兵牌尺寸、箭头参数、地形 hachure 参数
- **新增** Excalidraw 作为视觉设计工具：画 → 导出 roughjs 参数 → THEME_CONFIG
- **新增** 图标素材预渲染管线：SVG → 离屏 Canvas → ImageBitmap 缓存 → drawImage 贴图
- **修改** `map.js` 删除地理偏移相关代码（`_applyUnitOffsets`、`_onMapMoved`、`_renderComicUnitMarkers`）
- **修改** `CLAUDE.md` 删除"皮/骨分工"章节 + `generate_frontend` 工具条目，更新前端开发流程
- **移除** `generate_frontend` MCP 工具（Excalidraw + 现有代码库替代"画皮"能力）
- **移除** Turf.js 依赖（地理计算在像素空间用原生 Math + Haversine 替代）
- **移除** MapLibre `unit-banners` / `comic-unit-icons` symbol source/layer

**不含**（延后到独立 change）：React UI 面板（P2）、多尺度渲染策略（P3）。

## Capabilities

### New Capabilities
- `canvas-unit-renderer`: Canvas 2D + roughjs 部队兵牌和进攻箭头渲染，Path2D 缓存 + rAF 原生绘制
- `canvas-terrain-renderer`: roughjs hachure 参数梯度表达地形海拔差异（塬/坡/谷/河/隘口）
- `three-layer-canvas`: 按重绘频率分层的三层 Canvas 架构 + 独立脏标记
- `icon-preload-pipeline`: SVG 图标预渲染 → 离屏 Canvas 缓存 → drawImage 贴图管线
- `theme-config`: THEME_CONFIG 统一视觉参数配置（基于 Excalidraw 设计 + Qwen-VL analyze_ui 校对）

### Modified Capabilities
- `force-unit-visualization`: 渲染方式从 MapLibre symbol layer 改为 Canvas 2D + roughjs，删除地理偏移逻辑
- `campaign-map-rendering`: 新增三层 Canvas 覆盖层架构，MapLibre 降级为底图+投影服务
- `comic-style-tactical-theme`: 主题系统适配 roughjs 渲染（配置接口从 CSS 变量扩展为 roughjs 参数）

### Removed Capabilities
- `react-ui-panels`: 延后到 P2（独立 change），不在本次实施
- `multi-scale-rendering`: 延后到 P3（独立 change），不在本次实施

## Impact

- `static/js/canvasRenderer.js` — 新增（~350 行），三层 Canvas 架构 + roughjs + rAF 渲染引擎
- `static/js/terrainRenderer.js` — 新增（~120 行），roughjs hachure 地形渲染
- `static/js/map.js` — 删除地理偏移逻辑 + 旧的部队渲染代码（~200 行），接入 Canvas 渲染器
- `static/index.html` — 引入 roughjs (esm.sh CDN)，新增三层 Canvas 容器
- `static/assets/icons/` — 新增目录，预置 Game-icons.net CC 授权图标
- `mcp_server/qwen_mcp_server.py` — 删除 `generate_frontend` 工具定义
- `CLAUDE.md` — 更新工具清单、前端开发流程
- **BREAKING**: 前端 API 无变化，但地图渲染行为显著改变（roughjs 手绘风格替代 MapLibre symbol layer）
