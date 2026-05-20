## 1. 项目骨架与数据模型

- [x] 1.1 创建 Python 项目结构：`shaosongmap/` 包（`__init__.py`）、`static/` 目录、`tests/` 目录
- [x] 1.2 编写 `shaosongmap/models.py`：定义 `CampaignExtract`、`GeoFeature`、`CampaignMap` 三个 Pydantic 模型
- [x] 1.3 创建 `requirements.txt`：FastAPI、Pydantic、httpx、openai（DeepSeek 兼容）、uvicorn

## 2. Extractor 模块（战役文本提取）

- [x] 2.1 编写 `shaosongmap/extractor.py`：封装 DeepSeek API 调用，配置 `response_format: json_object`
- [x] 2.2 设计 Extractor 的 system prompt，定义 JSON 输出 schema（战役名、双方、兵力、地名、路线）
- [x] 2.3 实现 `extract()` 函数：接收文本 → 调用 DeepSeek → Pydantic 校验 → 返回 `CampaignExtract`

## 3. Geocoder 模块（古地名匹配）

- [x] 3.1 准备 CHGIS v6 数据集：将 CHGIS 地名数据解析为可查询格式（CSV/SQLite），含地名、经纬度、朝代时间范围
- [x] 3.2 编写 `shaosongmap/geocoder.py`：实现 `match_chgis()` 函数，模糊匹配 + 时间范围过滤
- [x] 3.3 实现 LLM 推断兜底 `infer_with_llm()`：接收未匹配地名 + 原文 → 调用 DeepSeek 推断近似坐标
- [x] 3.4 实现 `geocode()` 主函数：遍历地名列表 → CHGIS 匹配 → 失败则 LLM 推断 → 返回 `GeoFeature` 列表（含 `source` 字段）

## 4. FastAPI 应用

- [x] 4.1 编写 `app.py`：创建 FastAPI 应用，挂载 `static/` 目录，添加 CORS 中间件
- [x] 4.2 实现 `POST /api/extract` 端点：接收文本 → Extractor → Geocoder → 返回 GeoJSON 格式的 `CampaignMap`

## 5. 前端页面

- [x] 5.1 编写 `static/index.html`：页面布局（左侧 textarea + 右侧地图 + 底部结果面板）
- [x] 5.2 接入 MapLibre GL JS（CDN）：初始化地图，OpenStreetMap 底图
- [x] 5.3 实现提交逻辑：发送 POST /api/extract → 加载状态 → 解析返回 GeoJSON → 渲染地图标记和路线
- [x] 5.4 实现地图交互：地名标记（按 source 区分样式）、路线带箭头、点击气泡、图层切换

## 6. 测试

- [x] 6.1 编写 `tests/test_extractor.py`：mock DeepSeek API 响应，验证提取结果格式和必填字段
- [x] 6.2 编写 `tests/test_geocoder.py`：使用真实 CHGIS 样例数据 + mock LLM，验证匹配和兜底逻辑
- [x] 6.3 编写 `tests/test_api.py`：使用 FastAPI TestClient，验证端点集成测试（正常输入、空输入、错误响应）

## 7. 端到端验证

- [x] 7.1 准备一段《绍宋》战役样例文本，手动测试完整链路（文本 → 地图）
- [x] 7.2 验收 spec 中定义的所有 Scenario 均通过
