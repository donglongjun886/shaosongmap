# Place Icon Symbols

## Purpose

定义地图上地名标记的自定义 SVG 图标系统，使用城池和营寨符号替代圆点标记，实现古地图视觉风格。

## Requirements

### Requirement: 城池/营寨自定义图标标记

系统 SHALL 使用自定义 SVG 图标替代圆点标记地名，通过 MapLibre `addImage` + symbol 图层渲染。

图标类型 MUST：
- CHGIS 精确匹配地名：双线方框城池符号 ▭，描边色为墨色 `#2c2c2c`
- LLM 推断地名：三角营寨符号 ▲，填充色为赭石 `#8b4513`

图标 MUST 在 32×32 Canvas 上以 2x 分辨率绘制，确保 Retina 屏幕清晰。图标颜色、线宽 MUST 使用 CSS 变量对应的 JavaScript 常量值。

图标注册 MUST 在 `map.on('load')` 中现有数据层添加之前完成。

地名图层 MUST 从 `type: 'circle'` 迁移为 `type: 'symbol'`，使用 `icon-image` 和 `icon-size` 替代 `circle-radius` 和 `circle-color`。

#### Scenario: CHGIS 地名显示为城池图标

- **WHEN** 地图渲染一个 source 为 `chgis` 的地名
- **THEN** 该地名显示为双线方框城池符号，而非实心圆点

#### Scenario: LLM 推断地名显示为营寨图标

- **WHEN** 地图渲染一个 source 为 `llm_infer` 的地名
- **THEN** 该地名显示为三角营寨符号，而非空心圆点

#### Scenario: 灰显地名图标样式

- **WHEN** 地名在 timeline 中尚未到达当前步骤
- **THEN** 灰显图标应用 `icon-opacity: 0.35`，颜色变为灰色

#### Scenario: 图标随 zoom 缩放

- **WHEN** 用户缩放地图
- **THEN** 图标尺寸通过 `icon-size` zoom step 表达式自适应（同原 circle-radius 分段逻辑）