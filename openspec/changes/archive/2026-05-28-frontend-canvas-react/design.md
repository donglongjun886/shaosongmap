## Context

当前架构中，部队渲染使用 MapLibre symbol layer + 地理坐标偏移。核心矛盾：展示层问题在数据层解——像素间距和图标尺寸是纯前端概念，却在地理坐标空间做偏移计算，导致低 zoom 时偏移量爆炸（zoom 10 → 14km 偏移）。此方案已打三次补丁，每次只改参数不改架构，根本问题未解决。

同时，当前 1570 行 vanilla JS（已拆分为 5 文件但无模块化）全部使用全局变量管理状态，UI 面板（时间轴、图例、工具栏）通过直接 DOM 操作更新。这在单场景下可工作，但无法支撑攻城战→淞沪会战的多尺度演进。

**技术约束**：
- 前端零构建工具起步（P0 vanilla JS），P2 引入 React + esbuild
- MapLibre GL JS 4.7.1 为唯一的底图/投影库
- 古风渲染全部走 Canvas 2D，不依赖 WebGL 着色器
- 瓦片底图可选：小尺度纯色背景，大尺度 OpenFreeMap 矢量瓦片

## Goals / Non-Goals

**Goals:**
- Canvas 2D 接管所有部队和攻击箭头渲染，像素偏移自由控制，彻底删除地理偏移代码
- Canvas 2D 实现 LLM 推断地形的示意渲染（塬/坡/谷/河流）
- React 18 组件化所有 UI 面板（时间轴、图例、工具栏、部队列表），状态提升到 React 管理
- 多尺度渲染策略：zoom ≥ 14 Canvas 全控 + 纯色背景，zoom < 14 MapLibre 瓦片底图 + Canvas 叠加
- 绍宋漫画风视觉参数完整量化到 Canvas 绘制代码

**Non-Goals:**
- 不改变后端 API 接口（FastAPI 端点、Pydantic 模型不变）
- 不改变 CHGIS 地理编码管道
- 不引入 WebGL 自定义着色器（Canvas 2D 足够）
- 不引入状态管理库（React useState/useReducer 足够）
- P0 不做 React（先 Canvas + vanilla JS，定义好接口边界）

## Decisions

### Decision 1: Canvas 覆盖层架构

Canvas 作为 MapLibre 之上的透明覆盖层，通过 `map.project([lng, lat])` 将地理坐标转为屏幕像素坐标，在 `requestAnimationFrame` 循环中绘制。

```
┌─────────────────────────────────────────┐
│  <canvas> (position: absolute, 全覆盖)    │
│  - 部队兵牌、攻击箭头                      │
│  - 地形色块（塬/坡/谷/河）                 │
│  - 古风标注                               │
│  pointer-events: none (交互穿透到 MapLibre) │
├─────────────────────────────────────────┤
│  MapLibre GL (position: absolute)        │
│  - 底图瓦片 / 纯色背景                     │
│  - 地名标记 (symbol layer 保留)            │
│  - 行军路线 (line layer 保留)              │
│  - 投影转换 (map.project)                  │
└─────────────────────────────────────────┘
```

**理由**：Canvas 像素偏移不受 MapLibre layer 属性限制。`pointer-events: none` 保证地图交互不受影响。`rAF` 驱动渲染，自动跟随 MapLibre 的 move/zoom 事件。

**替代方案及淘汰原因**：
- ~~MapLibre custom layer (WebGL)~~：需要写 GLSL 着色器，古风渲染（毛笔笔触、朱砂印章）在 WebGL 中实现复杂度过高
- ~~纯 DOM markers~~：大量部队时 DOM 节点过多，性能差
- ~~Deck.gl~~：引入 40KB+ 依赖，且其 IconLayer 的碰撞检测对古风兵牌的形状不敏感

### Decision 2: rAF 渲染循环 + 脏标记

Canvas 使用 `requestAnimationFrame` 持续渲染，但通过 `dirty` 标记跳过无变化的帧：

```javascript
class CanvasRenderer {
  constructor() { this.dirty = true; this._startLoop(); }
  markDirty() { this.dirty = true; }
  _startLoop() {
    const loop = () => {
      if (this.dirty) { this._render(); this.dirty = false; }
      requestAnimationFrame(loop);
    };
    requestAnimationFrame(loop);
  }
}
```

MapLibre `moveend`、`zoomend`、数据更新时调用 `markDirty()`。

**理由**：rAF 保证与浏览器刷新率同步（60fps），脏标记避免闲置时浪费 GPU。大部分时间地图静止，rAF 循环仅做一次 `if (dirty)` 判断，开销可忽略。

**替代方案**：
- ~~事件驱动渲染（仅在 moveend 时绘制一次）~~：动画（部队生长、淡出）需要连续帧，事件驱动无法实现

### Decision 3: 多尺度渲染策略

| 尺度 | Zoom 范围 | 底图 | Canvas 渲染 |
|------|----------|------|------------|
| 攻城 | ≥ 16 | 纯色 `#f5f0e1` | 城墙、城门、街巷、攻守双方 |
| 战术 | 14-15 | 纯色 + 示意地形 | 兵牌、箭头、地形色块 |
| 战役 | 10-13 | OpenFreeMap 瓦片 | 部队、战略箭头、古风标注 |
| 会战 | ≤ 9 | OpenFreeMap 瓦片 | 兵团标注、战区箭头、印章 |

策略切换通过 `map.getZoom()` 判断，在 `_render()` 中分支。

**理由**：小尺度时现代瓦片（公路/建筑）是干扰，古战场和今天完全不同。大尺度时自然地理（长江、太湖、海岸线）大致不变，瓦片提供空间参照。

### Decision 4: 兵牌渲染参数（绍宋漫画风）

基于多轮 Qwen-VL 分析绍宋漫画截图 + 交叉验证的量化参数：

| 参数 | 值 | 说明 |
|------|-----|------|
| 卡片宽度 | 84px | 文字自适应 + padding |
| 卡片高度 | 56px | 固定 |
| 圆角半径 | 12px | 宽的 1/6 |
| 外边框 | 3px 阵营色 | 加粗主要轮廓 |
| 内边框 | 1px 墨色 `#2c2c2c` | 双层浮雕效果 |
| 色条 | 顶部 12px 阵营色 | 卡片分类标识 |
| 阴影 | `dropShadow(2, 3, 4, 0.25)` | Canvas filter |
| 字体 | 14px 'Noto Serif SC' | 部队名 |
| 箭头线宽 | 14px（卡片宽的 1/5） | 粗壮有笔触感 |
| 箭头头部 | 3:2 宽高比（近等边） | 漫画风格 |
| 箭头描边 | 1.5px 黑色 | 加强轮廓 |
| 箭头路径 | 带微弧贝塞尔 | 避免僵硬直线 |

### Decision 5: React 边界

React 仅管理 UI 面板（时间轴、图例、工具栏、部队列表），通过事件总线与 Canvas 渲染器通信：

```
React UI ←→ EventBus ←→ CanvasRenderer ←→ MapLibre
```

```javascript
// React → Canvas: 用户操作时间轴
eventBus.emit('timeline:step', { step: 3 });

// Canvas → React: 渲染完成通知
eventBus.emit('render:done', { unitCount: 4 });
```

**理由**：Canvas 天然是 imperative API，React 的声明式模型对它没有帮助。UI 面板正好相反——状态驱动的列表和表单正是 React 的长处。用事件总线解耦，后续任何一方可独立重构。

### Decision 6: 地形推理与渲染

LLM 从战役文本提取地形特征，程序化生成示意地形（非精确 DEM）：

```
输入: "焦文通部自东坡塬北侧列阵…沿干涸河沟隐蔽南下…娄室中军自塬底直冲"
LLM 输出: {
  "features": [
    { "type": "plateau", "name": "东坡塬", "center": [lng, lat], "radius_km": 2 },
    { "type": "gully", "name": "干涸河沟", "path": [[lng1,lat1], [lng2,lat2]] },
    { "type": "slope", "name": "塬底", "center": [lng, lat], "direction": "N"}
  ]
}
```

Canvas 根据地形类型绘制：
- **塬 (plateau)**：浅棕绿圆角矩形 + 密集短竖线（披麻皴）边缘
- **坡 (slope)**：渐变填充 + 稀疏短竖线
- **河沟 (gully)**：蓝色虚线曲线
- **谷 (valley)**：浅黄 V 形填充

### Decision 7: 前端构建工具

P0 阶段零构建（vanilla JS ES6 + Canvas API，浏览器原生支持）。P2 引入 React 时加入 esbuild：

```
esbuild static/js/react/index.jsx --bundle --outfile=static/js/react-bundle.js
```

**理由**：P0 交付速度优先，不引入构建链。P2 时 esbuild 比 webpack/vite 轻量 10 倍，适合本项目规模。

### Decision 8: roughjs 作为手绘风格渲染引擎

地形披麻皴、兵牌浮雕边框、毛笔笔锋箭头统一使用 roughjs 生成，不手写 Canvas 贝塞尔抖动和竖线循环。

**关键约束**（源自 Qwen3.7-Max 审计）：

1. **roughjs 仅用于生成阶段**，不在 rAF 热路径中实时计算。roughjs 靠算法生成大量随机线段模拟手绘，计算开销远超原生 Canvas API。在 60fps 循环中实时调用会导致 CPU 瓶颈和掉帧。

   ```
   初始化时（一次性）:
     roughGen.rectangle(params) → Path2D 对象 → 缓存到 Map

   rAF 每帧（热路径）:
     ctx.stroke(cachedPath2D)  // 原生 API, 极快
   ```

2. **使用局部相对坐标系**。roughjs 的抖动算法部分依赖于输入坐标的绝对值。若每帧传入屏幕绝对坐标，平移地图时线条抖动种子会偏移，产生"蠕动闪烁"。必须：生成时使用局部坐标系（图形中心为 0,0），渲染时 `ctx.translate()` 位移。

3. **固定 seed 保证渲染一致性**。同一图形的 seed 值在初始化时随机生成并持久化，后续帧复用相同 seed。

**与现有绘制代码的替代关系**：

| 现有手写代码 | roughjs 替代 | 代码量变化 |
|---|---|---|
| `_drawWideArrow()` 披麻皴箭头（~100行） | `roughGen.linearPath()` + `bowing: 1.5` + Path2D 缓存 | ~15行 |
| `_makeIconSVG()` 手绘图标（~30行） | `roughGen.rectangle()` + 离屏 Canvas | ~10行 |
| 地形披麻皴短竖线（~100行手写循环） | `roughGen.rectangle()` + `fillStyle: 'hachure'` + `hachureAngle: 90` | ~10行 |
| 兵牌双层边框（~30行手写 strokeRect） | `roughGen.rectangle()` + `fillStyle: 'solid'` | ~8行 |

**理由**：roughjs 的 hachure 填充样式天然产出古地图披麻皴/晕滃线效果。固定 seed 保证确定性输出。仅 10KB gzip。

**替代方案及淘汰原因**：
- ~~纯手写 Canvas~~：披麻皴 100+ 行循环、贝塞尔抖动等代码维护成本高
- ~~Konva.js~~：30KB，提供对象模型但我们需要的是手绘质感而非场景图管理
- ~~PixiJS WebGL~~：WebGL 管线与手绘风格冲突，roughjs 是 Canvas 2D 原生

### Decision 9: 三层 Canvas 替代单 Canvas

将 OpenSpec 原设计的单一 Canvas 覆盖层改为三个独立 Canvas 元素，按 z-index 分层：

```
z-index: 30  兵牌+箭头 Canvas  (unitCanvas)   — rAF 持续渲染，动态内容
z-index: 20  路线+地名 Canvas  (routeCanvas)  — 仅在时间轴步骤切换时重绘
z-index: 10  地形 Canvas       (terrainCanvas) — 仅在 zoom 跨 0.5 档时重绘
z-index: 0   MapLibre 底图
```

各层独立脏标记：
- `terrainCanvas`：`zoomDirty`（跨 0.5 zoom 阈值才触发）
- `routeCanvas`：`stepDirty`（时间轴步进触发）
- `unitCanvas`：`frameDirty`（rAF 每帧检查）

**关键约束**（源自 Qwen3.7-Max 审计）：

1. **MapLibre 动画期间的图层撕裂**：地图平滑缩放/平移动画时底图连续变化，若上层 Canvas 不重绘，图形会死死钉在屏幕原位。解决：动画期间对上层 Canvas 应用 CSS `transform: translate() scale()` 硬件加速跟随底图；`moveend`/`zoomend` 后重置 CSS transform 并触发真实重绘。**前提约束**：本项目强制禁用 MapLibre 的 `pitch`（倾斜）和 `bearing`（旋转），仅使用 2D 正交视图。当前代码未使用 3D 视图，若未来需要 3D 则改用 `map.getFreeCameraOptions()` 获取 4×4 矩阵。

2. **GPU 内存上限**：三个全屏 Canvas 在 4K/高 DPR 移动端可能超出浏览器限制。**降级算法**：优先降低 `devicePixelRatio`（2→1），其次限制逻辑尺寸（max 2048px）。废弃"合并为双层"的模糊说法，超限时直接降级为单层 Canvas（全部内容渲染到一个 Canvas 上），脏标记合并为单一 `frameDirty`。

3. **脏标记竞态**：快速缩放同时切换时间轴时，`zoomDirty` 和 `stepDirty` 可能同时为 true。定义优先级：`unitCanvas > routeCanvas > terrainCanvas`，同一帧内只触发一次统一渲染。地形重绘增加 **150ms 防抖** + **迟滞区间**（zoom > 10.6 才升级，< 10.4 才降级），避免临界值反复横跳。

**收益**：
- 时间轴步进时只重绘路线层，兵牌和地形层完全不动
- 缩放时只重绘地形层，兵牌层照常 rAF
- 兵牌生长动画（600ms 连续帧）只触及 unitCanvas

**参考**：Azgaar's Fantasy Map Generator 的 30+ 图层可拖拽排序架构。本项目简化为 3 层，按重绘频率分层而非按要素类型。

### Decision 10: 图标素材预渲染管线

城池/营寨/关隘等图标不再每帧用 Canvas 手绘（当前 `_makeIconSVG` 的做法），改为 SVG 素材预加载管线：

1. 图标来源：Game-icons.net（CC 授权历史战争图标）→ `static/assets/icons/`
2. 应用启动时：SVG → `Image` 对象 → 离屏 Canvas 光栅化 → 存入 `Map<string, HTMLCanvasElement>` 缓存
3. 渲染时：`ctx.drawImage(cachedCanvas, x, y, w, h)` 直接贴图

**注意**（源自 Qwen3.7-Max 审计）：`drawImage` 不接受 `ImageData`，正确做法是缓存为离屏 `HTMLCanvasElement` 或 `ImageBitmap`。

**DPI 适配**：固定屏幕大小的图标预渲染 1x/2x/3x 三档，按 `window.devicePixelRatio` 选择。随地图缩放的图标建议留在 MapLibre Symbol Layer 渲染。

**收益**：图标渲染从"每帧手绘矢量图形"变成"贴纹理"，单图标耗时从 ~0.3ms 降到 ~0.02ms。

### Decision 11: Excalidraw 作为视觉设计工具

兵牌卡片、进攻箭头、地形色块的视觉参数不在代码中反复试错，而是在 Excalidraw 中可视化设计：

```
Excalidraw 手绘 → 导出 .excalidraw JSON → 提取 roughjs 参数 → 写入 THEME_CONFIG
```

**理由**：Excalidraw 底层完全使用 roughjs 渲染，导出的 JSON 包含精确的 roughness / bowing / strokeWidth / seed 等参数。在 Excalidraw 中调整视觉效果所见即所得，比改代码→刷新浏览器→看效果快 10 倍。

### Decision 12: 移除 generate_frontend MCP 工具

`generate_frontend`（Qwen-VL-Max 生成前端视觉骨架）从 MCP 工具链中移除。

**理由**：
- CSS 布局/配色：已有成熟代码库，增量修改即可
- Canvas 兵牌绘制：Excalidraw + roughjs 参数直接复用替代
- 快速原型：analyze_ui 仍可用于截图诊断和参数提取

`analyze_ui` / `review_design` / `review_code` / `run_e2e_test` 四个工具保持不变。其中 `analyze_ui` 承担了新角色——"设计参数提取器"：截图 → analyze_ui 提取实际参数 → 与 THEME_CONFIG 对照 → 修正偏差。

### Decision 13: DPR 适配与生命周期管理

**Retina 屏幕适配**：
- 三层 Canvas 初始化时 `width/height = 逻辑尺寸 × devicePixelRatio`
- CSS `width/height` 设为逻辑尺寸
- 所有 Canvas 上下文中 `ctx.scale(dpr, dpr)`
- MapLibre 已有内置 DPR 处理，Canvas 层需独立适配

**生命周期管理**：
- rAF 循环在数据重新加载时 `cancelAnimationFrame` 旧循环，启动新循环
- MapLibre 事件监听器在数据更新时 `off` 旧回调，`on` 新回调
- 离屏 Canvas 和 `ImageBitmap` 在不需要时显式释放（置 null）

**依赖加载**（P0 无构建工具）：
- roughjs 通过 ESM CDN（`esm.sh`）加载，使用 Import Maps 保持模块化
- 避免全局变量污染，为 P2 平滑过渡到 esbuild 打包做准备
- 引入**资产预加载管理器**：`Promise.all` 等待所有 SVG、字体（`document.fonts.ready`）、roughjs 模块加载完毕后，再启动 MapLibre 和 Canvas 初始化与首帧渲染

**Turf.js 移除**：
- P0 阶段无构建工具，Turf.js CDN 全量包 ~60-80KB gzip
- 地理计算需求在像素空间中全部可用原生 Math 替代
- 箭头方位角：`Math.atan2(dy, dx)` 一行
- 箭头长度：`Math.hypot(dx, dy)` 一行
- 地形半径换算（km→像素）：手写 Haversine 公式 ~30 行。注意：经纬度坐标必须使用 Haversine（球面几何），禁止用平面 Math 直接计算经纬度距离
- P2 引入 esbuild 后如需 Tree-shaking 可按需重新评估

**roughjs 性能补充约束**（Qwen 二轮审计）：
- 地形多边形在传入 roughjs 前使用 **Douglas-Peucker 算法抽稀**，减少顶点数，避免 hachure 计算造成主线程阻塞
- **seed 生成策略**：`seed = hash32(graphicType + instanceId)`，确保同类不同实例有微小随机差异，同一实例重绘时一致。避免全局固定 seed 导致所有兵牌"复制粘贴感"
- **离屏 Canvas 内存管理**：Path2D 优先（内存极小）→ 离屏 Canvas 仅用于复杂 SVG 图标。地形等静态大要素合并到一个全局离屏 Canvas 中，而非每个多边形独立缓存。对图标缓存引入 **LRU 淘汰**（上限 50 个）

**已知限制**（P0 不处理，记录为技术债务）：
- Canvas 层的事件穿透和 Hit Testing（点击兵牌查看详情）暂不实现，保持 `pointer-events: none`，仅通过 MapLibre 底图的 click 事件获取地理坐标
- WebGL 上下文丢失（`webglcontextlost`）联动恢复暂不处理
- 截图/打印/导出时多层 Canvas + CSS transform 可能出现图层错乱
- Canvas 渲染内容对屏幕阅读器不可见，无 a11y 支持

## Risks / Trade-offs

- **[R]** roughjs 在 rAF 循环中实时计算导致性能崩溃 → **[M]** roughjs 仅用于初始化生成 Path2D/离屏 Canvas，rAF 热路径全程使用原生 Canvas API（`ctx.stroke(path)` + `ctx.drawImage(offscreen)`），单帧 < 2ms
- **[R]** 三层 Canvas 在 MapLibre 动画期间图层撕裂 → **[M]** 动画期间用 CSS `transform: translate() scale()` 硬件加速跟随底图，`moveend`/`zoomend` 后重置并真实重绘
- **[R]** roughjs 绝对坐标导致线条蠕动闪烁 → **[M]** 使用局部相对坐标系（图形中心为 0,0），渲染时 `ctx.translate()` 位移，roughjs 输入坐标始终不变
- **[R]** 三层 Canvas 在 4K/高 DPR 移动端 GPU 内存超限 → **[M]** 限制单 Canvas 最大物理像素 4096px，低端设备降级合并 routeCanvas + terrainCanvas 为单层
- **[R]** Canvas 绘制大量兵牌时性能下降 → **[M]** 兵牌通常 ≤ 10 个，每帧绘制 < 1ms。若未来扩展至百级，可加视口裁剪（仅绘制屏幕内的兵牌）
- **[R]** Canvas 文字渲染与 MapLibre 标签视觉不协调 → **[M]** 统一使用 Noto Serif SC 字体，Canvas 和 MapLibre 的 `text-font` 都指定同一字体
- **[R]** OpenFreeMap 国内访问不稳定 → **[M]** 小尺度不依赖瓦片；大尺度接受偶尔加载慢，非实时系统；未来可切天地图
- **[R]** LLM 地形推断可能不准确 → **[M]** 地形仅作示意，不影响核心的部队/路线数据。用户可通过编辑面板修正地名坐标
- **[R]** React 引入增加前端加载体积 → **[M]** React 18 production gzip ~12KB，esbuild bundle 整体 < 50KB gzip，可接受
- **[R]** Retina 屏幕 Canvas 渲染模糊 → **[M]** Canvas 初始化时 `width/height × devicePixelRatio` + `ctx.scale(dpr, dpr)`，CSS 尺寸保持逻辑像素
- **[R]** rAF 循环和事件监听器内存泄漏 → **[M]** 数据重新加载时 `cancelAnimationFrame` 旧循环 + `off` 旧回调，离屏 Canvas 显式释放
- **[R]** 复杂地形多边形 roughjs hachure 计算阻塞主线程 → **[M]** 提前用 Douglas-Peucker 抽稀多边形，合并为全局离屏 Canvas。若地形极度复杂，未来可迁至 Web Worker + OffscreenCanvas
- **[R]** 离屏 Canvas 缓存膨胀导致 OOM → **[M]** Path2D 优先（内存极小），离屏 Canvas 仅用于图标 + 地形合并单层，LRU 淘汰上限 50
- **[R]** 固定 seed 导致兵牌视觉重复 → **[M]** `seed = hash32(type + instanceId)`，同类不同实例有微小差异
- **[R]** 临界 zoom 级别反复触发地形重绘 → **[M]** 150ms 防抖 + 迟滞区间（±0.1 zoom）
- **[R]** SVG 异步加载时序导致首帧空白 → **[M]** 资产预加载管理器 `Promise.all` 等待全部就绪后启动渲染
- **[R]** Canvas 层完全覆盖底图导致地图无法交互 → **[M]** 保持 `pointer-events: none`，P0 不做 Hit Testing（已知限制）
- **[R]** WebGL 上下文丢失时 Canvas 层无联动 → **[M]** 已知限制，P0 不处理
- **[R]** 截图/打印/导出时多层 Canvas 错乱 → **[M]** 已知限制，P0 不处理

## Implementation Decisions（实现阶段新增，经 Qwen3.7-Max 三轮审计确认）

### Decision 14: 图标尺寸连续插值 + opacity-only 状态区分

原设计中 dim 图标使用独立的小尺寸 layer（0.1-0.55 scale），与 active 图标（0.4-1.2 scale）尺寸差异 3.2 倍，导致时间轴切换时图标剧烈跳动。经三轮讨论修正为：

- **icon-size**: MapLibre `["interpolate", ["linear"], ["zoom"], 6, 0.55, 10, 0.78, 14, 1.0]` 连续插值，不随 past/active/future 状态变化
- **状态区分**: 仅用 `icon-opacity`（Paint Property，原生支持 180ms transition）：past 0.5 / active 1.0 / future 0.4
- **dim 图层**: 使用与 active 相同的 icon-image 和 icon-size，不再单独加载 grayscale 小图标
- **关键约束**: `icon-size` 是 MapLibre Layout Property，不支持原生 transition。保持其不变避免了碰撞检测重排导致的掉帧和闪烁

### Decision 15: Canvas render 事件替代独立 rAF 循环

原设计使用独立 `requestAnimationFrame` 循环驱动 Canvas 渲染。经审计发现独立 rAF 与 MapLibre 渲染帧不同步（1-2 帧延迟），导致部队旗帜与地名图标相对抖动。

- **改用 `map.on('render')`** 触发 Canvas 重绘，与 MapLibre 严格同帧
- 移除 16ms 节流（高刷屏降帧 + 掉帧时撕裂）
- 移除 `map.on('move')` / `map.on('zoom')` / `map.on('moveend')` 事件处理

### Decision 16: 碰撞避让系统（AABB + 相对偏移 + smoothstep）

部队旗帜（Canvas）与地名图标（MapLibre）两套渲染系统独立运行，需要协调层防止重叠：

- **数据源**: `map.on('idle')` 时从 placeFeatures 数据缓存计算地名 AABB（JS 侧复现 icon-size interpolate 表达式 + measureText 动态文本宽度），不依赖 `queryRenderedFeatures`
- **碰撞算法**: 暴力 AABB，优先级排序（engaging > marching > deploying > retreating > routing），drawnFlags[] 累积防止部队间重叠
- **避让策略**: 方向变量双向避让（优先向北 → 超界切向南 → 双超放弃），每方向 3 次尝试
- **偏移量**: `targetOffsetY` 为相对值（计算 Y - 原始投影 Y），render 中每帧 `drawY = map.project().y + currentOffsetY`，拖动地图时不会错位
- **动画**: idle 计算 targetOffsetY → render 中 smoothstep(180ms) 过渡，deltaTime 上限 50ms 防切后台跳跃，新 idle 到达时中断当前动画无缝接续
- **已知妥协**（Qwen R3 确认）: drag/zoom 交互期间碰撞不更新（依赖 idle），可能短暂穿模；zoom 变化时重置偏移为 0

### Decision 17: 箭头拆分为 line 箭身 + drawImage 头精灵

原设计用单张 roughjs 箭头精灵 `scaleX` 拉伸，Qwen R3 指出会压扁箭头头部导致几何变形。修正为：

- **箭身**: `ctx.lineTo()` 程序化绘制，线宽 `lerp(zoom, 6→14, 6→14)`
- **箭头头**: 独立小精灵 `drawImage`，头宽 `min(线宽×1.5, 箭头总长×0.3)`
- **极短保护**: 总长 < 线宽×3 时 `lineCap='round'` 不画头，`lineW = max(1, lw×0.5)`

### Decision 18: 地图强制 2D 正交

碰撞检测使用 AABB（轴对齐包围盒），仅在 2D 正交投影下有效。增加硬约束：

- Map 初始化: `maxPitch: 0, maxBearing: 0`
- Canvas `pointer-events: none, z-index: 30`

### 实现阶段修正摘要

| 设计项 | 原设计 | 实现 |
|--------|--------|------|
| 渲染驱动 | rAF 独立循环 | map.on('render') 事件 |
| 图标状态区分 | dim 小图标 layer | icon-opacity 180ms transition |
| 图标尺寸 | step 离散分档 | interpolate 连续插值 |
| 碰撞数据源 | queryRenderedFeatures | JS 侧数据缓存 + measureText |
| 箭头渲染 | 单精灵 scaleX 拉伸 | lineTo 箭身 + drawImage 头 |
| roughjs 加载 | esm.sh ESM CDN | unpkg UMD 全局 `window.rough` |
| 地图旋转 | 未限制 | maxBearing: 0 强制禁止 |

## Migration Plan

### Decision 19: 箭头终点语义——direction_target 替代固定长度（2026-05-29 新增）

原设计箭头长度 = 固定像素值 `lerp(zoom, 90→200px)`，所有箭头一样长，与数据无关。经与 Qwen3.7-Max 讨论后改为语义驱动。

**方案设计**：
- 后端 `unit_states` schema 新增 `direction_target` 字段（LLM 从文本提取攻击目标地名/部队名，必须为 places/units 中已有名称）
- 前端 `setData` 时建 `name → geoCoord` HashMap（O(1) 渲染时查表）
- 渲染时：目标在视口内 → 箭头尖精确指向目标屏幕坐标；目标在视口外 → 截断到屏幕边缘；极短（<40px）→ 不画；查不到目标 → 不画
- `_drawArrow` 杆和头统一 seed（`seedBase`），消除 roughjs 随机偏移不匹配导致的接缝断痕

**参考**：Excalidraw、draw.io、Mermaid 等绘图工具的箭头都是"起点→终点"两坐标，没有固定长度概念。

### 阶段 1: P0 — Canvas 渲染引擎重构（本次，已完成）
1. 新增 `static/js/canvasRenderer.js`：三层 Canvas 架构 + roughjs + render 事件驱动（~430 行）
2. 新增 `static/js/terrainRenderer.js`：地形 hachure 参数梯度渲染（~120 行）
3. 修改 `static/js/map.js`：删除地理偏移代码 + 图标 interpolate + opacity-only dim + idle PlaceBounds + maxBearing
4. 修改 `static/index.html`：引入 roughjs (unpkg CDN)，新增 canvasRenderer/terrainRenderer
5. 修改 `mcp_server/qwen_mcp_server.py`：删除 `generate_frontend` 工具定义
6. 修改 `CLAUDE.md`：更新工具清单和前端开发流程
7. 新增 8 个 Game-icons.net SVG 图标（`static/assets/icons/`）
8. 自测通过（203 test passed, e2e Qwen-VL 视觉验证） → 就绪
9. 箭头改为 roughjs 每帧直接绘制（仿 Excalidraw，删除精灵缓存和分桶）
10. 箭头 seed 统一（杆和头同 seed，消除接缝断痕）
11. 箭头终点语义改为 direction_target 驱动（替代固定 arrowBaseLen）

### 阶段 2: P1 — Canvas 古风地形
1. 新增 `shaosongmap/terrain.py`：LLM 地形推理模块
2. `terrainRenderer.js` 中接入真实地形数据（当前 P0 仅实现渲染函数，数据用 mock）
3. Canvas 地形渲染

### 阶段 3: P2 — React UI 面板（独立 change）
1. 引入 esbuild + React 18 构建链
2. 新增 `static/js/react/`：React 18 组件（Timeline, Legend, Toolbar, UnitList）
3. `app.js` 中 UI 逻辑迁移到 React，保留 Canvas 渲染器不变

### 阶段 4: P3 — 多尺度适配（独立 change）
1. OpenFreeMap 瓦片接入
2. 多尺度渲染策略切换
3. 大尺度战略箭头/兵团标注

每个阶段独立可交付，不阻塞后续。P0 聚焦 Canvas 渲染正确性，React 和多尺度拆分为独立 change。

## Open Questions

- P1 地形推理是否需要独立 FastAPI 端点（`/api/terrain`），还是合并到现有 `/api/extract` 管道中？（建议合并，减少请求数）
- Game-icons.net 图标风格与绍宋漫画风的匹配度需实际验证，可能需要自绘部分关键图标
- P2 React 事件总线用自定义 EventTarget 还是引入 mitt（130 字节）？（建议 EventTarget，零依赖）
- 三层 Canvas 的高 DPI 移动端表现需在实际设备上测试验证
