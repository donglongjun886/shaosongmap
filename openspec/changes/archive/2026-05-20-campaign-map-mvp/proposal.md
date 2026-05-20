## Why

《绍宋》等历史小说中，古代地名与现代差异巨大，山川河流布局直接决定战役走向，但读者缺乏直观的地理认知——不知道「汴京」在哪、「汉水」如何阻隔行军、「襄阳」到「唐州」之间有什么地形障碍。读者需要一个工具，能把一段战役文字自动变成可交互的地图，让「边读边看地图」成为可能。

## What Changes

- 新增 `POST /api/extract` 端点：接收战役文本，返回结构化 JSON（含 GeoJSON 格式的地图数据）
- 新增 `extractor` 模块：调用 DeepSeek API 从战役文本中提取战役名、将领、兵力、地名序列、行军路线
- 新增 `geocoder` 模块：通过 CHGIS v6 数据集将古地名匹配为经纬度坐标，匹配失败时由 LLM 根据上下文推断近似坐标
- 新增前端页面 `static/index.html`：textarea 粘贴文本 → 提交 → MapLibre GL JS 渲染交互式地图

## Capabilities

### New Capabilities

- `campaign-text-extraction`: 接收一段中文战役/行军文本，调用 DeepSeek API 提取结构化数据（战役名称、参战双方、将领、兵力、地名列表、行军路线），输出 Pydantic 校验后的 JSON
- `ancient-place-geocoding`: 接收古地名列表，优先通过 CHGIS v6 数据集精确匹配经纬度，匹配失败时由 LLM 根据文本上下文推断近似坐标，所有结果标注数据来源（chgis / llm_infer）
- `campaign-map-rendering`: 前端接收 GeoJSON 格式的战役数据，通过 MapLibre GL JS + OpenStreetMap 瓦片渲染交互式地图，支持缩放、点击地名查看详情、显示/隐藏路线图层

### Modified Capabilities

<!-- 首次变更，无已有能力可修改 -->

## Impact

- **新增依赖**: DeepSeek API（云服务）、CHGIS v6 数据集（本地文件）、MapLibre GL JS（CDN）
- **新增代码**: `shaosongmap/` 包（extractor.py, geocoder.py, models.py）、`app.py`（FastAPI 入口）、`static/index.html`（前端）
- **测试覆盖**: extractor.py 和 geocoder.py 需编写 pytest 单元测试
- **部署影响**: 无现有系统，全新部署
