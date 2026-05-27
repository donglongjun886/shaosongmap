## 1. 后端：槽位标记替代偏移计算

- [ ] 1.1 `make_unit_geojson()` 中为每个部队 feature 添加 `_slot` 属性——同坐标按名称序分配 0/1/2
- [ ] 1.2 删除 `compute_unit_offsets()` 函数及 `import math`
- [ ] 1.3 坐标返回真实经纬度（不再加偏移），仅 `_slot` 属性传递排序信息
- [ ] 1.4 运行现有测试，确认 `TestComputeUnitOffsets` 类全部失败

## 2. 前端：自适应偏移计算

- [ ] 2.1 新增 `_groupUnitsByCoord(unitFeatures)` 按 `[lng, lat]` 分组部队
- [ ] 2.2 新增 `_applyUnitOffsets(unitFeatures, zoom, isComic)` 函数，使用 `m_per_px = 156543 * cos(midLat) / 2^zoom` 计算偏移
- [ ] 2.3 comic 主题图标宽度 84px，banner 主题 26px，间距 = 图标宽度 × 1.3
- [ ] 2.4 在 `updateMap()` 中调用 `_applyUnitOffsets()` 后再 `setData()`
- [ ] 2.5 `_renderComicUnitMarkers()` 中复用同样的偏移后的坐标
- [ ] 2.6 方向线起点坐标跟随锚点偏移同步更新

## 3. 自适应缩放

- [ ] 3.1 添加 `map.on('moveend', ...)` 监听，debounce 100ms 后重新计算偏移
- [ ] 3.2 缩放后重新 `setData()` 更新 unit-banners、unit-directions、comic-unit-icons 三个源
- [ ] 3.3 性能验证：多次缩放不出现明显卡顿

## 4. 测试更新

- [ ] 4.1 删除 `tests/test_unit_banner.py` 中 `TestComputeUnitOffsets` 类（5 个测试）
- [ ] 4.2 新增 `test_slot_assignment`：验证同坐标多部队 _slot 分配、不同坐标各得 slot=0
- [ ] 4.3 新增前端纯函数测试：`_groupUnitsByCoord` 和偏移计算公式
- [ ] 4.4 `test_unit_banner.py` 中 `TestMakeUnitGeojson` 验证 feature 包含 `_slot` 属性
- [ ] 4.5 全量测试通过，覆盖率不低于 88%

## 5. 端到端验证

- [ ] 5.1 `scripts/selftest.py` 验证：控制台无错误、部队与地点无重叠
- [ ] 5.2 手动验证：tactical/comic 模式下缩放地图，部队间距保持视觉一致
- [ ] 5.3 手动验证：battle 模式下部队使用较小的 banner 间距
