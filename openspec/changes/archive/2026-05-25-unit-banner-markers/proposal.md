## Why

当前部队渲染使用 NATO APP-6A 风格的块状箭头（Polygon 填充），与项目追求的汉代《驻军图》古地图风格不协调。路线已使用朱砂虚线+箭头、地名已使用城池/营寨图标，独部队标记风格突兀，需要统一为汉代军事地图的"双线套框旗帜"风格。

## What Changes

- **BREAKING** 删除 `_make_block_arrow_polygon` 函数，移除块状箭头 Polygon 生成逻辑
- 新增 `_offset_point` 工具函数，用于沿方向角偏移坐标
- 新增 `_make_unit_banner_features`，生成 Point（旗帜位置）+ LineString（方向线）特征对
- 重写 `_make_unit_geojson`，使用 `_feature_type` 属性区分特征类型
- 前端新增 `_makeBannerIcon` Canvas 绘制函数，生成双线套框旗帜图标
- 前端新增 `unit-banners` / `unit-directions` 数据源及 4 个渲染图层
- 前端删除旧 `unit-arrows` 数据源及 3 个图层
- 图例更新为旗帜风格色块

## Capabilities

### New Capabilities

_无新增能力。_

### Modified Capabilities

- `force-unit-visualization`: 部队渲染从 NATO 块状箭头改为汉代《驻军图》旗帜标记 + 方向指示线

## Impact

| 文件 | 影响 |
|------|------|
| `app.py` | 删除 `_make_block_arrow_polygon`，新增 `_offset_point`、`_make_unit_banner_features`，重写 `_make_unit_geojson` |
| `static/index.html` | 新增 `_makeBannerIcon`、4 个 banner 图标、2 个新 source、4 个新 layer，删除旧 arrow source/layer，更新 `updateMap`/`applyTimelineFilters`/`toggleUnitLayers`/图例 |
| `tests/test_force_unit.py` | 删除块状箭头测试，新增 `TestUnitBannerFeatures`（6 个测试） |
