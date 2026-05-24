## Context

Phase 1+2 已完成底图架构和自适应尺寸，但整体视觉风格仍偏现代。本次在已有架构上做纯视觉层重构，不改逻辑。

## Goals / Non-Goals

**Goals:**
- 配色从 Web 标准色切换为古地图传统中国色
- 字体切换为衬线中文字体系列
- 地名标记从圆点改为城池/营寨 SVG 图标
- 行军路线从实线改为虚线+箭镞
- 背景叠加宣纸纹理
- 地图区域添加卷轴边框

**Non-Goals:**
- 不改任何数据结构或 API
- 不引入外部字体 CDN（仅用系统自带）
- 不改部队箭头核心几何逻辑（仅调整配色）

## Decisions

### 1. 配色色板

```css
--paper:    #f2e8d5  /* 宣纸本色 */
--vermillion: #c23b22  /* 朱砂红，行军路线/交战 */
--indigo:   #2b4c7e  /* 靛蓝，宋军 */
--ochre:    #8b4513  /* 赭石棕，金军 */
--ink:      #2c2c2c  /* 墨色，地名标签/轮廓 */
--sage:     #5a7a6a  /* 青灰，山脉 */
```

替代方案：使用更鲜艳的配色 → 不选，古地图讲究沉稳克制。

### 2. 字体栈

```css
font-family:
  "KaiTi", "STKaiti", "楷体",           /* macOS/iOS 楷体 */
  "Songti SC", "SimSun", "宋体",        /* macOS/iOS 宋体 */
  "Noto Serif SC",                       /* Android/Linux */
  serif;                                  /* 终极回退 */
```

仅用系统自带字体，零外部加载。标题用楷体，正文用宋体系列。

### 3. 城池图标生成

MapLibre `map.addImage()` 注册 SVG 图标，用 Canvas 离屏渲染：

```javascript
function makeIcon(type, color, size) {
  const canvas = document.createElement('canvas');
  canvas.width = size; canvas.height = size;
  const ctx = canvas.getContext('2d');
  if (type === 'fortress') {
    // 双线方框 + 中心点
    ctx.strokeStyle = color; ctx.lineWidth = 2;
    ctx.strokeRect(3, 3, size-6, size-6);
    ctx.strokeRect(6, 6, size-12, size-12);
  } else {
    // 三角营寨
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.moveTo(size/2, 2); ctx.lineTo(size-2, size-3); ctx.lineTo(2, size-3);
    ctx.fill();
  }
  return { width: size, height: size, data: new Uint8Array(canvas.toDataURL(...)) };
}
```

MapLibre 的 addImage 支持 ImageData 或 HTMLImageElement。

### 4. 路线样式

- `line-dasharray`: `[4, 3]` 朱砂色虚线
- 大箭镞：symbol 层用 `symbol-placement: 'line'` + `symbol-spacing: 200`，图标为自定义三角 SVG

### 5. 纹理叠加

CSS `::after` 伪元素 + 内联 SVG feTurbulence filter：

```css
background-image: url("data:image/svg+xml,<svg...><filter><feTurbulence/></filter></svg>");
opacity: 0.06;
pointer-events: none;
```

不增加 HTTP 请求，不消耗性能。

### 6. 卷轴边框

纯 CSS：
```css
.map-wrap {
  border: 2px solid var(--ink);
  box-shadow: inset 0 0 20px rgba(0,0,0,0.05);
}
```

## Risks / Trade-offs

- 系统自带楷体/宋体在不同平台效果不一 → 字体栈覆盖 macOS/iOS/Windows/Android
- SVG icon 在高分辨率下可能模糊 → 用 2x Canvas (32×32) 适配 Retina
- 纹理叠加在 dark mode 下可能不可见 → opacity 0.06 在浅色背景生效，后续 dark mode 另行处理