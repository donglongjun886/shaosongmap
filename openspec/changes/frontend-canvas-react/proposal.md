## Why

MapLibre symbol layer 的同坐标多部队偏移方案（地理坐标偏移）三次补丁仍未根治——低 zoom 时偏移量爆炸（zoom 10 → 14km）。且当前 vanilla JS 单体状态管理无法支撑攻城战→淞沪会战的多尺度演进。需要从渲染层到底层重构，用 Canvas 接管视觉表现、React 接管 UI 状态。

## What Changes

- **新增** Canvas 2D 渲染覆盖层，替代 MapLibre symbol layer 渲染部队兵牌和进攻箭头，像素偏移自由控制
- **新增** Canvas 古风地形渲染，LLM 从战役文本推断地形特征（塬/坡/谷/河），程序化生成示意地形
- **新增** React 18 组件化 UI 面板（时间轴、图例、工具栏、部队列表），替代当前 vanilla JS DOM 操作
- **新增** 多尺度渲染策略：小尺度（zoom ≥ 14）Canvas 全控 + 纯色背景，大尺度（zoom < 14）MapLibre 瓦片底图 + Canvas 叠加
- **修改** `map.js` 删除地理偏移相关代码（`_applyUnitOffsets`、`_onMapMoved` 偏移重算）
- **修改** `unit_banner.py` 坐标保持真实值，不再做偏移计算
- **移除** MapLibre `unit-banners` symbol source/layer

## Capabilities

### New Capabilities
- `canvas-unit-renderer`: Canvas 2D 部队兵牌和进攻箭头渲染，像素偏移 + 碰撞避让 + 绍宋漫画风
- `canvas-terrain-renderer`: LLM 文本推断地形特征，程序化生成示意地形（塬/坡/谷/河流）
- `react-ui-panels`: React 18 组件化 UI（时间轴/图例/工具栏/部队列表），状态提升到 React 管理
- `multi-scale-rendering`: 缩放级别自适应的渲染策略切换（纯色背景 ↔ 瓦片底图）

### Modified Capabilities
- `force-unit-visualization`: 渲染方式从 MapLibre symbol layer 改为 Canvas 2D，删除地理偏移逻辑
- `campaign-map-rendering`: 新增 Canvas 覆盖层架构，MapLibre 降级为底图+投影服务
- `timeline-interaction-ui`: UI 层从 vanilla JS DOM 操作迁移为 React 组件
- `comic-style-tactical-theme`: 主题系统适配 Canvas 渲染（配置接口从 CSS 变量扩展为 Canvas 绘制参数）

## Impact

- `static/js/map.js` — 删除地理偏移逻辑（~100 行），接入 Canvas 渲染器
- `static/js/canvasRenderer.js` — 新增（~400 行），Canvas 渲染引擎
- `static/js/terrainRenderer.js` — 新增（~200 行），地形渲染
- `static/js/app.js` — UI 逻辑拆分，为 React 迁移准备接口边界
- `static/js/react/` — 新增目录，React 组件（P2）
- `shaosongmap/services/unit_banner.py` — 删除偏移计算，坐标保持真实值
- `shaosongmap/extractor.py` — 新增地形特征提取（或独立 terrain 模块）
- `static/index.html` — 引用新脚本，挂载 React 根节点
- **BREAKING**: 前端 API 无变化，但地图渲染行为显著改变（像素偏移替代地理偏移）
