## Why

当前视觉语言是现代 Web 地图风格（Google Maps 式圆点、Unicode 箭头、鲜红亮蓝配色、系统无衬线字体），与历史战役场景严重不协调。需要全面替换为古地图视觉体系——仿宣纸质感、朱砂/靛蓝/墨色传统中国色、城池符号、手绘行军线、衬线中文字体。

## What Changes

6 个优先级分三轮实施：

**第一轮 (P1+P2)——配色 + 字体**：
- 全页面色板替换：背景纸色→宣纸本色，宋军→靛蓝 #2b4c7e，金军→赭石 #8b4513，路线→朱砂 #c23b22，标签→墨色 #2c2c2c
- 字体系统：全局中文字体切换为衬线系列（Songti/KaiTi/Noto Serif SC）

**第二轮 (P3)——地名标记**：
- 圆点(circle) → 城池/营寨图标(symbol)，自定义 SVG icon-image
- CHGIS 精确地名用双线方框 ▭，LLM 推断地名用三角 ▲

**第三轮 (P4+P5+P6)——路线 + 纹理 + 边框**：
- 实线行军线 → 朱砂虚线 + 大箭镞符号
- 背景叠加 SVG noise 纹理模拟宣纸颗粒感
- 地图区域添加卷轴式边框

## Capabilities

### New Capabilities
- `place-icon-symbols`: 城池/营寨自定义 SVG 图标标记系统

### Modified Capabilities
- `basemap-provider`: 背景增加纹理叠加层
- `campaign-map-rendering`: 配色体系、字体系统、地名标记样式、路线样式、边框装饰
- `force-unit-visualization`: 阵营配色调整（蓝/红→靛蓝/赭石）

## Impact

- `static/index.html`: CSS 配色变量、字体声明、地图图层样式、SVG 图标注册、纹理叠加、边框装饰
- 无后端变更
- 无 API 变更
- 无新依赖（字体用系统自带衬线中文字体）