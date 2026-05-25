## Context

当前系统在 tactical/battle/strategic 三个 scale 级别使用统一的汉代驻军图视觉体系（双线套框旗帜、朱砂红+靛青配色、楷体标注）。《绍宋》漫画源材料中的交战态势图采用完全不同的视觉语言——信息图风格、阵营色分色、宋体标注、红色印章——两者视觉割裂。

Tactical 级（1-10km 局部战场）元素少（3-7 个标记），纯色背景显得空旷，是引入漫画风格的最佳切入点。Battle/strategic 级保留现有样式不变。

## Goals / Non-Goals

**Goals:**
- Tactical 级引入绍宋漫画视觉主题，与漫画源材料的交战态势图风格统一
- 阵营色系统让读者不看文字即能区分金军/宋军
- 地形色块填充战术图的空白区域
- 所有改动限制在 CSS + JS 图层，不修改 MapLibre GL 渲染管线

**Non-Goals:**
- 不改变 battle/strategic 级的现有视觉样式
- 不修改后端 API、Extractor、Geocoder
- 不引入新的外部依赖（如 Canvas 库、图片资源）
- 不实现完整的手绘渲染引擎（Phase 3 探索方向，暂不落地）

## Decisions

### 1. CSS 自定义属性驱动的主题切换

**选择**：在 `#map` 容器上通过 CSS class（`.theme-comic`）切换战术级视觉主题，所有子元素通过 CSS 自定义属性继承。

**原因**：比 JS 逐元素修改样式更简洁，比 Canvas overlay 改动量更小。一个 class 切换即可覆盖所有图层。

**备选方案**：
- Canvas overlay：灵活但需要独立渲染管线，与现有 MapLibre 图层协调复杂
- 独立 HTML 模板：维护两套模板成本高

### 2. 阵营色通过 CSS 变量映射

**选择**：定义 `--faction-song`（宋军蓝 #2b4c7e）和 `--faction-jin`（金军红 #c23b22），GeoJSON properties 中的 `faction` 字段映射到 CSS class。

**原因**：漫画中金军用红色、宋军用蓝色是固定惯例。CSS 变量让箭头/标记/路线统一着色。

### 3. 地形色块用 MapLibre fill layer 实现

**选择**：为 `place_type` 为 mountain/mountain_pass/river/valley 的地名生成对应的 fill layer（半透明色块），仅 tactical 级显示。

**色块映射**：
- `mountain` / `mountain_pass`：浅棕绿色块 `rgba(139,119,101,0.15)`
- `river`：浅蓝色曲线带 `rgba(100,149,237,0.2)`
- `valley` / `region`：浅黄色块 `rgba(218,195,125,0.15)`

**原因**：利用现有 GeoJSON 数据（地的坐标），以该点为中心生成固定半径的色块区，无需后端改动。

### 4. 部队标记 双线套框 → 阵营色填充框（仅 tactical）

**选择**：Tactical 级用 `image` 类型的 symbol layer 渲染阵营色矩形框+白字，替换当前的 HTML marker 双线套框。用 Canvas 离线生成不同阵营的 icon image。

**原因**：漫画中的「阿里军」标记是红底白字矩形框。用 MapLibre `addImage()` 动态生成 icon，性能优于 HTML marker。

### 5. 红色印章用固定定位 div + SVG

**选择**：印章不在地图图层内，而是作为 `position: absolute` 的 div 覆盖在地图容器角落，用内联 SVG 绘制。

**印章样式**：朱砂红 `#c23b22`，正方形，45度旋转，汉印白文风格，文字为战役名（≤4字）。

**原因**：印章不随地图缩放/平移，固定在地图容器右下角。CSS transform 实现旋转，不依赖外部图片。

### 6. Tactical 级字体切宋体

**选择**：`.theme-comic` 下所有文字标签使用 `font-family: "SimSun", "Songti SC", "Noto Serif SC", serif`。

**原因**：漫画地图地名标注使用宋体，比楷体更贴近信息图风格。

## Risks / Trade-offs

- **Canvas 生成 icon 的性能**：每个部队需生成一个 icon image → 部队数量≤10，影响可忽略
- **地形色块精度**：以单点坐标生成固定半径色块是示意性的，不是真实地形范围 → Tactical 级本就是示意，可接受
- **宋体在非中文系统可能回退到衬线体** → font-family 链包含多个 fallback
- **印章文字超 4 字时拥挤** → JS 动态调整字号

## Open Questions

- 是否需要在 comic 主题下为不同阵营的部队框使用不同底色（宋军蓝底白字 / 金军红底白字）？提案阶段暂定统一按阵营着色
- 地形色块半径是否需要根据数据对角线自适应？初步固定为数据对角线 × 5%