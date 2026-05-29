## 1. P0: Canvas 渲染引擎

- [x] 1.1 新增 `static/js/canvasRenderer.js`：初始化三层 Canvas（terrainCanvas / routeCanvas / unitCanvas），尺寸跟随 MapLibre 容器，DPR 适配（`width/height × devicePixelRatio` + `ctx.scale(dpr, dpr)`）
- [x] 1.2 引入 roughjs：通过 unpkg CDN 加载 UMD 包 `rough.bundled.js`，保持全局 `rough` 可用
- [x] 1.3 实现 rAF 渲染循环 + 三层独立脏标记：`zoomDirty`（zoom 跨 0.5 档触发）/ `stepDirty`（时间轴步进触发）/ `frameDirty`（rAF 每帧检查），优先级 unitCanvas > routeCanvas > terrainCanvas
- [x] 1.4 实现 MapLibre 动画期间 CSS transform 同步：`move`/`zoom` 事件中对上层 Canvas 应用 `transform: translate() scale()` 硬件加速跟随底图；`moveend`/`zoomend` 后重置 transform + 触发真实重绘
- [x] 1.5 实现 `map.project()` 坐标转换 + 视口裁剪（仅绘制屏幕内元素）
- [x] 1.6 实现生命周期管理：`cancelAnimationFrame` 旧循环、`off` 旧事件监听器、离屏 Canvas 显式释放
- [x] 1.7 限制单 Canvas 最大物理像素 4096px，低端设备降级（dpr 降至 1）

## 2. P0: roughjs 兵牌与箭头渲染

- [x] 2.1 定义 `THEME_CONFIG` 配置对象：阵营色（宋 `#2b4c7e` / 金 `#8b4513` / 交战 `#e63946`）、兵牌尺寸（84×56px / 圆角 12px / 顶部色条 12px）、箭头参数（线宽 14px / 头部 3:2 / bowing 1.5）、roughness 0.8
- [x] 2.2 实现兵牌卡片生成函数：初始化时离屏 Canvas 绘制（含色条、双层边框），rAF 中 `ctx.drawImage(offscreenCard, x, y)` 贴图
- [x] 2.3 实现进攻箭头生成函数：初始化时 roughjs 在离屏 Canvas 绘制标准箭头精灵，rAF 中 `ctx.translate() + rotate() + scale() + drawImage()` 变换绘制
- [x] 2.4 实现同坐标多部队像素偏移（按 `_slot` 沿南北排列，64px 间距）。偏移为纯像素操作，不修改地理坐标
- [ ] 2.5 实现碰撞避让（AABB 检测，兵牌与地名标记重叠时优先向北偏移，最多尝试 3 次）— P0 已知限制，暂未实现
- [x] 2.6 所有离屏 Canvas 在精灵生成时使用固定坐标，渲染时 `ctx.translate()` 位移，消除蠕动闪烁

## 3. P0: 图标素材预渲染管线

- [ ] 3.1 从 Game-icons.net 筛选 CC 授权图标（城池/营寨/关隘/旌旗），放入 `static/assets/icons/` — 目录已创建，图标待筛选
- [x] 3.2 实现图标预渲染：应用启动时 SVG → `Image` → 离屏 Canvas 光栅化 → `Map<string, HTMLCanvasElement>` 缓存 — 基础管线已实现
- [x] 3.3 DPI 适配：固定屏幕大小图标按 `devicePixelRatio` 处理，Canvas DPR scale 已实现
- [x] 3.4 渲染时 `ctx.drawImage(cachedIcon, x, y, w, h)` 直接贴图 — 兵牌和箭头精灵使用此模式

## 4. P0: 清理旧渲染代码

- [x] 4.1 `map.js` 删除 `_applyUnitOffsets()` 函数及所有调用
- [x] 4.2 `map.js` 删除 `_onMapMoved` 偏移重算监听
- [x] 4.3 `map.js` 删除 `unit-banners` 和 `comic-unit-icons` MapLibre source/layer 的 active 使用（tactical 模式隐藏，非 tactical 保留兼容）
- [x] 4.4 `map.js` 删除 `_renderComicUnitMarkers()` 函数
- [x] 4.5 `map.js` 接入 Canvas 渲染器（`updateMap()` 中调用 `CanvasRenderer.setData()` + `CanvasRenderer.markDirty()`）
- [x] 4.6 保留 `_drawWideArrow` 作为备选（当 roughjs 路径不支持时回退），标记为 deprecated

## 5. P0: 状态动画（简化版）

- [x] 5.1 实现部队首次出现生长动画：通过 `globalAlpha` 渐变 + arrow 精灵变换
- [x] 5.3 实现溃散碎裂效果：opacity 递减（retreating 0.5, routing 0.3）

## 6. P0: MapLibre 事件集成

- [x] 6.1 `map.on('moveend')` 回调中调用 `canvasRenderer.markDirty()`
- [x] 6.2 `map.on('zoomend')` 回调中检查尺度级别切换，更新渲染策略
- [x] 6.3 `map.on('resize')` 回调中同步三层 Canvas 元素尺寸 + DPR 重算

## 7. P0: 前端 HTML 更新

- [x] 7.1 `static/index.html` 新增三层 Canvas 容器（由 CanvasRenderer 动态创建）
- [x] 7.2 `static/index.html` 引入 roughjs UMD 包（unpkg CDN）
- [x] 7.3 删除 Turf.js 相关引用（已有代码中未使用 Turf.js）
- [x] 7.4 确保所有 Canvas `pointer-events: none`，交互穿透到 MapLibre

## 8. P0: MCP 工具链清理

- [x] 8.1 `mcp_server/qwen_mcp_server.py` 删除 `generate_frontend` 工具定义
- [x] 8.2 `CLAUDE.md` 更新工具清单：移除 `generate_frontend` 行
- [x] 8.3 `CLAUDE.md` 更新前端开发流程：删除"皮/骨分工"章节，新增 Excalidraw + roughjs 设计管线描述
- [x] 8.4 `CLAUDE.md` 更新"前端开发完整流程"为新的设计→实现→审查→自测流程

## 9. P0: 自测验证

- [ ] 9.1 手动测试：输入默认战役文本，验证兵牌渲染正确（数量/位置/颜色/roughjs 手绘质感）
- [ ] 9.2 手动测试：缩放地图，验证三层 Canvas 无图层撕裂、无抖动、无蠕动
- [ ] 9.3 手动测试：时间轴步进，验证路线层正确切换、兵牌动画正常
- [ ] 9.4 手动测试：Retina 屏幕验证 Canvas 清晰度（DPR 适配）
- [ ] 9.5 运行 `python scripts/selftest.py`，程序化检查 + Qwen-VL 视觉验证
- [ ] 9.6 运行 `uv run pytest tests/ -v --cov=shaosongmap`，确保测试全部通过

## 10. P1: LLM 地形推理

- [ ] 10.1 新增 `shaosongmap/terrain.py`：LLM 地形特征提取模块
- [ ] 10.2 在 `/api/extract` 管道中集成地形推理
- [ ] 10.3 扩展 Pydantic 模型：新增 `TerrainFeature` 数据模型
- [ ] 10.4 编写地形提取单元测试

## 11. P1: Canvas 地形 roughjs 渲染

- [ ] 11.1 `terrainRenderer.js` 实现塬地渲染：`roughGen.rectangle()` + `fillStyle: 'hachure'` + `hachureAngle: 75` + `fillWeight: 0.8`，固定 seed 缓存 Path2D
- [ ] 11.2 实现坡地渲染：渐变填充 + roughjs hachure 稀疏斜线（`hachureGap: 8`, `hachureAngle: 60`）
- [ ] 11.3 实现河沟渲染：roughjs curve + `strokeDasharray` + 蓝色 `#6495ed`
- [ ] 11.4 实现谷地渲染：浅黄 V 形填充 + roughjs 密集竖线（`hachureAngle: 90`, `hachureGap: 2`）
- [ ] 11.5 实现隘口渲染：双线收窄标记
- [ ] 11.6 实现地形 zoom 自适应：tactical（zoom ≥ 14）完整 hachure → battle（10-13）简化 → strategic（≤ 9）仅色块
- [ ] 11.7 确保地形 z-index：底图 < 地形(terrainCanvas) < 路线(routeCanvas) < 兵牌(unitCanvas) < MapLibre 地名标签

## 12. P2: React 基础设施（独立 change）

- [ ] 12.1 新增 `package.json`（esbuild + React 18 依赖）
- [ ] 12.2 新增 esbuild 构建脚本（`static/js/react/` → `static/js/react-bundle.js`）
- [ ] 12.3 新增 `static/js/react/index.jsx`：React 根组件 + 挂载点
- [ ] 12.4 新增 `static/js/react/EventBus.js`：EventTarget 事件总线模块
- [ ] 12.5 `static/index.html` 添加 `#react-ui` 容器 + 引用 `react-bundle.js`
- [ ] 12.6 实现 `Timeline` 组件 + `Legend` 组件 + `Toolbar` 组件 + `UnitList` 组件
- [ ] 12.7 `app.js` 中删除被 React 替代的 UI 操作代码

## 13. P3: 多尺度渲染（独立 change）

- [ ] 13.1 实现四级尺度分类函数 `getScaleLevel(zoom)`：siege/tactical/battle/strategic
- [ ] 13.2 实现底图动态切换（纯色背景 ↔ OpenFreeMap 瓦片，带滞回带）
- [ ] 13.3 实现部队兵牌尺度自适应（完整卡片 → 简化 → 圆点编号）
- [ ] 13.4 实现行军路线尺度自适应（粗实线 → 虚线 → 细虚线）
- [ ] 13.5 实现地名标签密度自适应（全部 → 重要 → 仅城市）

## 14. 收尾

- [ ] 14.1 运行全量质量门禁：`uv run pre-commit run --all-files`
- [ ] 14.2 运行全量测试：`PYTHONPATH=. uv run pytest tests/ -v --cov=shaosongmap`
- [ ] 14.3 代码审查：调用 `review_code` MCP 工具做异源审查
- [ ] 14.4 端到端自测：调用 `run_e2e_test` MCP 工具验证前端渲染
