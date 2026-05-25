## Why

Tactical 级地图目前沿用 battle/strategic 级的汉代驻军图视觉体系，与《绍宋》漫画源材料的视觉语言割裂。漫画中自带交战态势图，风格为彩色信息图+水墨纸本质感——读者从漫画切换到地图时应感到视觉连贯。且 tactical 级元素少（3-7个标记），纯色背景显得空旷，引入地形色块和漫画装饰可让画面饱满。

## What Changes

- Tactical 级引入绍宋漫画视觉主题，battle/strategic 级保持不变
- **阵营色系统**：金军红色系、宋军蓝色系，箭头/部队框/路线按阵营着色，读者不看字即知谁是谁
- **部队标记**：tactical 级从汉代双线套框切换为阵营色填充矩形框+白字（参考漫画「阿里军」红底白字框）
- **地形色块**：利用 LLM 已提取的 `place_type`，tactical 级以半透明色块渲染山/河/谷
- **箭头风格**：加粗+毛笔笔触感（起笔顿点+收笔尖锋），阵营色
- **字体**：tactical 级切为宋体（SimSun/Noto Serif SC），更贴近漫画信息图风格
- **红色印章**：SVG 实现，角落装饰，内容为战役名
- **标注底框**：地名标签加半透明白底，防止被地形色块干扰

## Capabilities

### New Capabilities

- `comic-style-tactical-theme`: Tactical 级地图的绍宋漫画视觉主题，包括阵营色系统、地形色块、印章装饰、漫画风格部队标记、毛笔笔触箭头

### Modified Capabilities

- `force-unit-visualization`: Tactical 级部队标记从双线套框改为阵营色填充矩形框+白字，battle/strategic 级保持原样式不变
- `campaign-map-rendering`: Tactical 级新增地形色块渲染层、印章装饰层、标注底框；字体从楷体切换为宋体
- `basemap-provider`: Tactical 级 schematic 底图扩展为纸纹理+地形色块组合，不再仅纯色

## Impact

- `static/index.html`：主要改动区，CSS 样式（阵营色变量、comic 主题类、字体）、JS 图层逻辑（按 scale 切换视觉主题、地形色块渲染、印章生成）
- `shaosongmap/extractor.py`：不影响（LLM 已提取 `place_type`，无需改动）
- `shaosongmap/models.py`：不影响（GeoFeature 已有 `place_type` 字段）
- MapLibre GL 渲染管线：不改动，纯 CSS + JS 图层叠加实现
