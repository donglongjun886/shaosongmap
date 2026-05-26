## Context

`static/index.html` (1570行) 是项目唯一的前端文件，HTML 骨架、CSS 样式、JavaScript 逻辑全部混在一起。约 50 个函数/变量在全局作用域，约 313 处 DOM/标识符引用。修改代码需要在三种语言间反复跳转，也难以做代码审查。maplibre-gl 的 CDN 引用缺少 SRI hash。

## Goals / Non-Goals

**Goals:**
- 将 HTML/CSS/JS 拆分为独立文件，CSS 和 JS 按职责进一步分模块
- 为 CDN 资源添加 SRI integrity hash
- 对无 DOM 依赖的纯函数编写 pytest 单元测试
- 拆分后功能完全不变，加载顺序正确

**Non-Goals:**
- 不引入 Node.js 构建工具链（Vite/Webpack）
- 不引入前端测试框架
- 不做 JS 模块化（ES modules）——保持 IIFE/全局作用域兼容
- 不做 CSS/JS 压缩——这是构建工具链的范畴

## Decisions

### 1. 文件拆分方案：4 文件结构

```
static/
├── index.html      (~160行) HTML 骨架
├── css/
│   └── map.css     (~150行) 所有样式
└── js/
    ├── utils.js    (~40行)  纯函数：escHtml、颜色计算、距离计算
    ├── map.js      (~700行) 地图初始化、底图、图标、comic 主题
    └── app.js      (~540行) 应用逻辑：OCR、提取、SSE、编辑、时间轴
```

**为什么是 2 个 JS 文件而非更多？** 当前所有 JS 共享全局状态（map 实例、_lastExtractData 等变量），拆太细会导致循环依赖或加载顺序复杂化。按「渲染层 vs 交互层」一分为二是自然边界。

**为什么不是 ES modules？** `<script type="module">` 的 defer 语义会延迟执行，而当前代码中 `map.on('load')` 在 script 顶层注册，依赖即时执行。迁移到 module 需要改造初始化时序，收益不值得复杂度。

### 2. JS 拆分边界

**map.js（渲染核心）**：地图初始化、BASEMAP 配置、applyBasemap、所有地图图层注册、图标生成函数（_makeIconSVG、_makeBannerIcon、_makeComicUnitIcon）、popup、comic 主题渲染（_applyComicTheme、_renderSeal、_renderTerrainBlocks、_renderComicUnitMarkers、_applyComicRouteStyle、_applyComicLabelHalo）、updateMap、applyTimelineFilters、toggleLayer、toggleUnitLayers

**app.js（交互逻辑）**：错误捕获、模式切换、批量 OCR（drop zone → SSE → merge）、analyze/extract SSE、状态管理、可编辑面板（render → collect → reRender）、时间轴交互（stepTo → renderTimeline → renderEventCard → renderUnitStateCard）、键盘快捷键

**utils.js（纯函数）**：`escHtml`、`_darkenColor`、`_factionColor`、`_computeDataDiagonal`、`_terrainColorForType`——均无 DOM 依赖，可直接单测

### 3. 前端测试方案：pytest 直接测试纯函数

**为什么用 pytest 而非 Jest/Vitest？** 纯函数不依赖 DOM/浏览器 API，用 Python 的 exec 或 js2py 即可验证。保持在 Python 技术栈内，不引入 Node.js 测试框架。

**测试范围**：仅 `utils.js` 中的 5 个纯函数，每个 2-3 个用例。不测试 DOM 操作和地图 API 调用（那需要浏览器环境）。

**测试文件**：`tests/test_frontend_utils.py`，直接用 Python 逻辑复现 JS 函数的等价行为进行验证。

### 3. SRI Hash 获取

maplibre-gl@4.7.1 的 integrity hash 从 unpkg CDN 或 SRI hash generator 获取。格式：`sha384-<base64>`

```html
<script src="https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.js"
  integrity="sha384-<hash>" crossorigin="anonymous"></script>
<link href="https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.css"
  rel="stylesheet" integrity="sha384-<hash>" crossorigin="anonymous">
```

### 5. 加载顺序

拆分后 script 按 `utils.js → map.js → app.js` 顺序加载。浏览器并行下载但串行执行，天然保证依赖关系。不需 async/defer。

## Risks / Trade-offs

- [加载性能] 拆分后从 1 个 HTML 请求变为 4 个（HTML + CSS + 2JS），多 3 个请求 → 文件量小（~20KB CSS + ~25KB JS），HTTP/2 多路复用下开销可忽略
- [缓存收益] 拆开后 CSS/JS 可单独缓存，迭代时通常只改一个文件 → 浏览器只需重新下载变更部分
- [回归风险] 拆分是纯机械操作，不改逻辑 → 通过截图对比、API 测试和 utils 纯函数单测验证
- [测试覆盖] 仅测试纯函数，DOM/地图交互不在测试范围 → 截图审查仍是主要验证手段，这是轻量方案的权衡