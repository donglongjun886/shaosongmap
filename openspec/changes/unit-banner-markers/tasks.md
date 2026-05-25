## 1. 后端：旗帜标记生成

- [x] 1.1 新增 `_offset_point` 工具函数（沿角度偏移坐标）
- [x] 1.2 新增 `_make_unit_banner_features`（生成 Point + LineString 特征对）
- [x] 1.3 重写 `_make_unit_geojson`，调用 `_make_unit_banner_features`，使用 `_feature_type` 属性
- [x] 1.4 删除 `_make_block_arrow_polygon` 函数

## 2. 测试：更新 test_force_unit.py

- [x] 2.1 删除旧块状箭头测试（`test_basic_arrow`、`test_arrow_south_direction`）
- [x] 2.2 新增 `TestUnitBannerFeatures` 类（6 个测试）
- [x] 2.3 保留 `test_angle_for_direction` 独立函数

## 3. 前端：旗帜图标 + 新图层体系

- [x] 3.1 新增 `_makeBannerIcon(color, size)` Canvas 绘制函数
- [x] 3.2 注册 4 个旗帜图标（banner-song / banner-jin / banner-engaging / banner-dim）
- [x] 3.3 新增 `unit-banners` 和 `unit-directions` GeoJSON 数据源
- [x] 3.4 新增 4 个渲染图层（banner-icon / banner-label / direction-line / direction-arrow）
- [x] 3.5 删除旧 `unit-arrows` 数据源及 3 个图层

## 4. 前端：交互适配

- [x] 4.1 更新 `updateMap` 特征分类为 `_feature_type` 属性
- [x] 4.2 更新 `applyTimelineFilters` 图层引用
- [x] 4.3 更新 `toggleUnitLayers` 图层引用
- [x] 4.4 更新图例 HTML（旗帜色块替代 ◆ 符号）
- [x] 4.5 更新 click/hover 事件处理指向新图层

## 5. 验证

- [x] 5.1 全部 108 个测试通过
- [x] 5.2 JavaScript 语法检查通过
- [x] 5.3 无残留旧图层引用
