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

## Risks / Trade-offs

- **[R]** Canvas 绘制大量兵牌时性能下降 → **[M]** 兵牌通常 ≤ 10 个，每帧绘制 < 1ms。若未来扩展至百级，可加视口裁剪（仅绘制屏幕内的兵牌）
- **[R]** Canvas 文字渲染与 MapLibre 标签视觉不协调 → **[M]** 统一使用 Noto Serif SC 字体，Canvas 和 MapLibre 的 `text-font` 都指定同一字体
- **[R]** OpenFreeMap 国内访问不稳定 → **[M]** 小尺度不依赖瓦片；大尺度接受偶尔加载慢，非实时系统；未来可切天地图
- **[R]** LLM 地形推断可能不准确 → **[M]** 地形仅作示意，不影响核心的部队/路线数据。用户可通过编辑面板修正地名坐标
- **[R]** React 引入增加前端加载体积 → **[M]** React 18 production gzip ~12KB，esbuild bundle 整体 < 50KB gzip，可接受

## Migration Plan

### 阶段 1: P0 — Canvas 部队渲染层（本次）
1. 新增 `static/js/canvasRenderer.js`（~400 行）
2. 修改 `static/js/map.js`：删除地理偏移代码，接入 Canvas 渲染器
3. 修改 `shaosongmap/services/unit_banner.py`：坐标保持真实值，删除偏移计算
4. 自测通过 → 部署

### 阶段 2: P1 — Canvas 古风地形
1. 新增 `shaosongmap/terrain.py`：LLM 地形推理模块
2. 新增 `static/js/terrainRenderer.js`：Canvas 地形绘制
3. 前端接入地形数据

### 阶段 3: P2 — React UI 面板
1. 新增 `static/js/react/`：React 18 组件（Timeline, Legend, Toolbar, UnitList）
2. 新增 esbuild 构建脚本（package.json + build 命令）
3. `app.js` 中 UI 逻辑迁移到 React，保留 Canvas 渲染器不变

### 阶段 4: P3 — 多尺度适配
1. OpenFreeMap 瓦片接入
2. 多尺度渲染策略切换
3. 大尺度战略箭头/兵团标注

每个阶段独立可交付，不阻塞后续。

## Open Questions

- P1 地形推理是否需要独立 FastAPI 端点（`/api/terrain`），还是合并到现有 `/api/extract` 管道中？（建议合并，减少请求数）
- P2 React 事件总线用自定义 EventTarget 还是引入 mitt（130 字节）？（建议 EventTarget，零依赖）
