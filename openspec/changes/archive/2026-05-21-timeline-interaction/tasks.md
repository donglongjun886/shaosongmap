## 1. 数据模型

- [x] 1.1 新增 `TimelineEventType` 枚举（march / battle / encamp / retreat）
- [x] 1.2 新增 `TimelineEvent` Pydantic 模型（seq, event_type, description, actors, places_involved）
- [x] 1.3 新增 `CampaignTimeline` 模型，继承 `CampaignExtract` 并添加 `events: list[TimelineEvent]` 字段

## 2. LLM 提取器

- [x] 2.1 编写 `_TIMELINE_SYSTEM_PROMPT`，在现有 prompt 基础上增加事件序列提取规则
- [x] 2.2 实现 `extract_timeline(text, model)` 函数，调用 DeepSeek API 返回 `CampaignTimeline`
- [x] 2.3 在 `extract_timeline` 中加入 Pydantic 校验，格式不合法时抛出 ValueError

## 3. 后端 API

- [x] 3.1 `ExtractRequest` 新增可选字段 `mode: str | None = None`（"timeline" / "static"）
- [x] 3.2 SSE 管道根据 `mode` 调用不同提取函数，timeline 模式时进度事件包含事件数量
- [x] 3.3 `_make_geojson` 扩展：每个 feature 的 properties 中注入 `step` 属性（从 TimelineEvent 推导）
- [x] 3.4 最终 `result` 事件返回的 `geojson` 包含 step 标注，同时返回 `events` 数组和 `total_steps`

## 4. 前端时间轴 UI

- [x] 4.1 在 `index.html` 结果面板区域新增时间轴进度条组件（圆点节点 + 连接线）
- [x] 4.2 新增「上一步」「下一步」按钮，实现 `currentStep` 状态管理和按钮禁用逻辑
- [x] 4.3 新增事件描述卡片，显示当前事件的序号、类型标签、描述文本、参与方和地名
- [x] 4.4 绑定步进按钮到地图 filter：`map.setFilter()` 按 step 过滤 feature 可见性
- [x] 4.5 实现地名标记样式切换：当前步未激活的地名使用灰色半透明，激活的地名使用完整样式
- [x] 4.6 进度条节点点击跳转到对应步骤

## 5. 测试

- [x] 5.1 编写 `test_extract_timeline`：提供含时序军事行动的文本，验证返回的 events 数组结构完整
- [x] 5.2 编写 `test_extract_timeline_empty`：提供无军事行动的文本，验证 events 为空数组
- [x] 5.3 编写 `test_timeline_model_validation`：提供非法 events 数据，验证 Pydantic 抛出 ValidationError
