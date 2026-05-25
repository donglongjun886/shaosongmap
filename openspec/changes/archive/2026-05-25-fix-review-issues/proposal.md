## Why

Qwen-VL 视觉审查发现三个影响用户体验的问题：LLM 对阵营识别不准确导致部队标记颜色错误（宋军显示为黑色而非蓝色）、方向字段提取率低导致部分部队无线条指示、行军路线虚线在视觉上呈现"断开"效果。这些问题根因在提取管道和后端渲染，修复后部队标记颜色、方向指示、路线连续性将有明显改善。

## What Changes

- **LLM 提取 Prompt 增强**：在 timeline 系统提示词中新增阵营识别规则，要求 LLM 从历史语境推断每个阵营的正方/反方角色，并将 ForceUnit.faction 与 factions[].name 对齐
- **LLM 方向提取强化**：强化规则 7 的措辞和示例，提高 direction 字段的提取覆盖率
- **行军路线虚线优化**：将 route-lines 的 dash pattern 从 `[8,4]` 收紧为 `[6,3]`，减少视觉断裂感；comic 主题下改用更紧凑的 `[6,3]`
- **路线锚点标记**：在路线 GeoJSON 的 LineString 首末点添加起止标记（circle layer），使路线与地名/部队标记之间的空间关系更清晰

## Capabilities

### New Capabilities
<!-- No new capabilities introduced -->

### Modified Capabilities
- `campaign-text-extraction`: LLM 提取 prompt 中新增阵营识别规则和方向提取强化
- `campaign-map-rendering`: 行军路线虚线样式和锚点标记图层
- `force-unit-extraction`: 方向字段提取规则强化

## Impact

- `shaosongmap/extractor.py`: `_TIMELINE_SYSTEM_PROMPT` 和 `_SYSTEM_PROMPT` 修改
- `static/index.html`: 路线样式 dash pattern、新增锚点 circle layer
- `app.py`: `_make_geojson()` 路线 feature 生成逻辑（如需锚点数据注入）
- `tests/test_extractor.py`: 可能需要调整测试用例中的预期阵营/方向值