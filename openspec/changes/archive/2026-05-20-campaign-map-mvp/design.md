## Context

ShaosongMap 是一个全新项目，当前代码库仅有 `CLAUDE.md` 和 OpenSpec 结构。MVP 需要从零搭建「战役文本 → 结构化数据 → 古地名匹配 → 地图渲染」的完整链路。约束：单人开发、MVP 快速验证核心假设（从小说段落能否产出有用的地图）。

## Goals / Non-Goals

**Goals:**
- 提供 `POST /api/extract` API，接收战役文本并返回包含 GeoJSON 的结构化 JSON
- 通过 DeepSeek API 提取战役文本中的结构化信息（战役名、双方将领、兵力、地名、路线）
- 通过 CHGIS v6 数据集将古地名匹配为精确经纬度，匹配失败时 LLM 兜底
- 提供单页面 HTML 前端，包含文本输入区、MapLibre GL JS 地图、提取结果面板

**Non-Goals:**
- 不引入数据库（MVP 无状态，纯请求-响应）
- 不引入 React 或前端构建工具（单 HTML + CDN）
- 不做用户认证、历史记录、分享功能
- 不做浏览器插件
- 不做高精度地形渲染（底图用 OpenStreetMap）

## Decisions

### 1. 架构分层

```
routers (app.py) → services (extractor / geocoder) → external (DeepSeek API / CHGIS 文件)
```

- **决定**: MVP 阶段不引入 repository 层（无数据库），services 直接访问外部资源
- **理由**: 降低前期抽象成本，等需要缓存或持久化 CHGIS 查询结果时再引入
- **备选方案**: 一开始就建 repository 层 → 否决，MVP 不需要

### 2. Extractor：纯 LLM 提取，不做后处理

- **决定**: DeepSeek API 调用时使用 `response_format: json_object`，Pydantic 校验输出格式，不做额外的规则正则后处理
- **理由**: 战役文本相对结构化，LLM 对中文命名实体提取准确率高；后处理规则难以覆盖所有情况，MVP 先观察常见错误类型再迭代
- **备选方案**: LLM + 正则规则后处理 → 延迟到发现具体问题时引入

### 3. Geocoder：CHGIS 为主，LLM 推断兜底

- **决定**: 地名优先在 CHGIS v6 中做精确匹配（地名 + 朝代），匹配分数低于阈值或未命中时，调用 LLM 根据文本上下文推断近似坐标，所有结果标注 `source` 字段（`chgis` / `llm_infer`）
- **理由**: CHGIS 是学术界公认的历史地理数据集，坐标可靠；LLM 推断可能有偏移但覆盖山川河流等 CHGIS 不包含的地理实体
- **备选方案**: 纯 CHGIS（覆盖率不够）或纯 LLM（幻觉风险高）

### 4. 前端：单 HTML + CDN，不引入框架

- **决定**: 一个 `static/index.html`，通过 `<script>` 标签 CDN 引入 MapLibre GL JS，纯 JavaScript 调用 `/api/extract` 并渲染地图
- **理由**: MVP 只有一个页面一个功能，React/Vue 等框架只会增加构建链路和维护负担；验证假设后如果需要，可以迁移到 React
- **备选方案**: React + MapLibre GL JS → 框架开销大于功能收益，延迟到前端变复杂时

### 5. 数据契约：Pydantic 模型

- **决定**: 使用 Pydantic 定义 `CampaignExtract`（提取层输出）、`GeoFeature`（地名+坐标+来源）、`CampaignMap`（API 最终输出含 GeoJSON），Extractor 和 Geocoder 之间通过 Pydantic 模型传递数据
- **理由**: 类型安全、自动校验、FastAPI 原生集成、自动生成 OpenAPI schema

### 6. 无状态 API

- **决定**: `POST /api/extract` 每次接收完整文本，处理后直接返回结果，不存储任何状态
- **理由**: MVP 验证的是提取+匹配+渲染链路，持久化需求不明确；等产品验证通过后，再讨论是否需要保存历史

## Risks / Trade-offs

- **[DeepSeek API 稳定性]** → API 可能超时或限流，MVP 阶段不做重试/降级，仅返回错误信息给前端
- **[CHGIS 数据覆盖不全]** → 部分古地名（尤其是小村庄、临时驻扎地）不在 CHGIS 中，通过 LLM 推断兜底，但坐标精度会下降
- **[LLM 输出格式漂移]** → 即使有 `response_format` 约束，LLM 偶尔会输出不符合预期的结构，通过 Pydantic 校验捕获并返回 422 错误
- **[单 HTML 首次加载 MapLibre GL JS]** → CDN 加载约 200KB，首次打开有延迟，MVP 可接受
- **[OpenStreetMap 对中国古代地名标注不足]** → OSM 是现代底图，古代地名无标注；我们用 MapLibre 的 layer 机制叠加古地名标记，不依赖底图本身的地名标注
