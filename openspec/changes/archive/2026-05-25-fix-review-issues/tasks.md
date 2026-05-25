## 1. 阵营识别 Prompt 增强

- [x] 1.1 在 `_TIMELINE_SYSTEM_PROMPT` 中新增规则 10：阵营标准化识别规则（标准称谓、历史常识推断、与 ForceUnit.faction 对齐）
- [x] 1.2 在 `_SYSTEM_PROMPT`（static 模式）中同步新增阵营标准化规则
- [x] 1.3 运行 `tests/test_extractor.py` 现有测试确认无回归

## 2. 方向提取 Prompt 强化

- [x] 2.1 重写 `_TIMELINE_SYSTEM_PROMPT` 规则 7：增加 direction 正反例说明（据守→null、仰攻→方向、迂回包抄→方向、侧翼压上→null*）
- [x] 2.2 运行 `tests/test_extractor.py` 确认 direction 相关测试通过

## 3. 行军路线虚线样式

- [x] 3.1 将 `static/index.html` 中 `route-lines` layer 默认 `line-dasharray` 从 `[8, 4]` 改为 `[6, 3]`
- [x] 3.2 将 `_applyComicRouteStyle()` 中 comic 主题的 `line-dasharray` 从 `[10, 5]` 改为 `[6, 3]`

## 4. 路线端点锚点标记

- [x] 4.1 在 `static/index.html` 的 `map.on('load')` 中注册 `route-anchors` GeoJSON source（空 FeatureCollection）和 circle layer
- [x] 4.2 在 `updateMap()` 中从 route LineString features 提取首末坐标，更新 `route-anchors` source
- [x] 4.3 在 comic 主题切换时确保锚点图层不受 `_applyComicRouteStyle()` 影响

## 5. 端到端验证

- [x] 5.1 启动服务器，运行 `python scripts/automate_review.py` 生成截图和审查报告
- [x] 5.2 确认审查报告中阵营色标记正确（宋军蓝色、金军红色）
- [x] 5.3 确认审查报告中路线虚线无"断裂"误报
- [x] 5.4 确认审查报告无 JS 运行时错误
