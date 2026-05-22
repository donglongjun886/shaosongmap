## 任务

- [x] 修复 `_compute_unit_offsets` 坐标翻倍 bug（返回 delta 而非绝对坐标）
- [x] 修复 `line-dasharray` 表达式不兼容 MapLibre 4.7（改为常量）
- [x] 前端图层操作加 `_safeFilter`/`_safeLayout` 防御检查
- [x] 改进 LLM prompt：direction 硬约束为八标准方位词
- [x] 改进 LLM prompt：unit_states 强制覆盖所有 event actors
- [x] `extract_timeline` 增加 null 字段清洗
- [x] `_compute_unit_offsets` 按实际坐标分组（非地名）
# 此处无需标记，tests 和验证均已通过