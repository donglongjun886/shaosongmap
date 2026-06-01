## 1. 后端 - 删除文件

- [x] 1.1 删除 `shaosongmap/services/unit_banner.py`
- [x] 1.2 删除 `static/js/tacticalRenderer.js`
- [x] 1.3 删除 `static/js/canvasRenderer.js`
- [x] 1.4 删除 `static/js/terrainRenderer.js`
- [x] 1.5 删除 `static/debug-terrain.html`
- [x] 1.6 删除 `static/debug-styles.html`

## 2. 后端 - 修改代码

- [x] 2.1 `extractor.py`：删除 `extract_timeline`、`_TIMELINE_SYSTEM_PROMPT`、`_validate_unit_states`；简化 `_SYSTEM_PROMPT`（去掉 events/unit_states/direction/scale 规则）
- [x] 2.2 `models.py`：删除 `UnitState`、`ForceUnit`、`CampaignTimeline`、`MilitaryScale`
- [x] 2.3 `pipeline.py`：删除 mode 参数和 timeline 分支，删除 unit_states/events/scale 处理
- [x] 2.4 `services/geo.py`：删除 `angle_for_direction`、`offset_point`、`_DYNASTY_YEARS`（如果仅 unit_banner 使用）
- [x] 2.5 `routers/extract.py`：删除 mode 参数
- [x] 2.6 `schemas.py`：删除 mode 字段、ExtractResponse 中 events/units/unit_states/scale/total_steps

## 3. 前端 - 修改代码

- [x] 3.1 `map.js`：删除 `CanvasRenderer.init/setData/setTimeline` 调用，删除部队相关 layer
- [x] 3.2 `index.html`：删除时间轴复选框、roughjs CDN、tacticalRenderer/terrainRenderer 引用
- [x] 3.3 `app.js`：删除 `_currentScale`/`_renderTactical`/`_tacticalTimeline`/`_tacticalInited`/mode；简化 `handleSSEEvent`/`reRender`/`stepTo`/`switchToInputMode`；删除 SSE timeline UI 代码
- [x] 3.4 `utils.js`：删除仅被已删文件引用的函数

## 4. 测试更新

- [x] 4.1 删除 `test_unit_banner.py`
- [x] 4.2 删除 `test_geo.py` 中 `angle_for_direction` 和 `offset_point` 相关测试
- [x] 4.3 更新 `test_frontend_utils.py` 中 JS 加载顺序测试
- [x] 4.4 更新 `test_extractor.py` 中与 timeline 相关的测试
- [x] 4.5 运行全量测试确保通过
