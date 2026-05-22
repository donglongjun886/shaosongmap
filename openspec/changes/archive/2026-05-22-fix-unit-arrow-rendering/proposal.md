# fix-unit-arrow-rendering

## 问题

force-unit-timeline 功能上线后发现三个 Bug：

1. **箭头坐标翻倍**：`_compute_unit_offsets` 返回绝对坐标而非差值，导致 `_make_unit_geojson` 中 `base + offset` 使坐标翻倍（lon 109→217），箭头跑到北极圈
2. **MapLibre 4.7 不支持 data-driven `line-dasharray`**：`['match', ...]` 表达式导致 `unit-arrow-outline` 图层创建失败，后续 setFilter 报 `non-existing layer`
3. **LLM 部队状态覆盖不全、方向缺失**：只有主角部队有 unit_states，direction 返回「侧翼」「塬底」等非标准值

## 修复

1. `_compute_unit_offsets` 返回坐标差值（delta），移除 `base +`
2. `line-dasharray` 改为常量 `[1, 0]`，同时给 `applyTimelineFilters` 和 `toggleUnitLayers` 加 `_safeFilter`/`_safeLayout` 防御检查
3. 更新 LLM prompt：direction 硬约束为八标准方位词，unit_states 强制覆盖所有 event actors
4. 偏移分组从「地名」改为「坐标 tuple」，解决异名同坐标重叠
5. `extract_timeline` 增加 null 字段清洗（LLM 返回 null 时替换为 ""）