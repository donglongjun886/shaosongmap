## Why

当前系统将战役文本压缩为一张静态地图，丢失了战争叙事中最核心的时间维度。读者无法感知「岳飞从襄阳出发→途经唐州→在颍昌决战→金军溃退」的时序推进，所有地名和路线同时呈现在地图上，混乱且不符合阅读体验。此次变更为地图引入时间轴，让读者「边读边推进」。

## What Changes

- 新增 `TimelineEvent` 和 `CampaignTimeline` 数据模型，将战役分解为有序事件序列
- Extractor 新增 `extract_timeline()` 函数，通过改良 prompt 让 LLM 输出包含事件序列的结构化数据
- 前端新增时间轴进度条和「上一步/下一步」按钮，支持逐步推进查看战役进程
- GeoJSON 生成改为增量模式：每个 feature 标注所属 step，前端按当前 step 过滤渲染
- 路线在推进时动态生长、回退时收缩；地名标记在事件触发时高亮

## Capabilities

### New Capabilities

- `timeline-extraction`: LLM 从战役文本中按时间顺序提取事件序列（行军/战斗/扎营/撤退），每个事件包含序号、类型、描述、参与方和涉及地名
- `timeline-interaction-ui`: 前端时间轴交互控件——进度条 + 步进按钮 + 事件描述卡片，驱动地图增量渲染

### Modified Capabilities

- `campaign-text-extraction`: 提取需求扩展——LLM 输出新增 `events` 数组，按时间顺序分解军事行动
- `campaign-map-rendering`: 地图渲染需求扩展——支持按 step 过滤 feature、路线动态生长/回缩、地名标记按事件高亮

## Impact

- `shaosongmap/models.py`：新增 `TimelineEventType`、`TimelineEvent`、`CampaignTimeline` 模型
- `shaosongmap/extractor.py`：新增 `extract_timeline()` 函数及对应 system prompt
- `app.py`：`/api/extract` SSE 管道支持 timeline 模式，最终结果包含 per-step GeoJSON
- `static/index.html`：新增时间轴 UI 组件（进度条、步进按钮、事件卡片）和 step 状态管理逻辑
- `tests/test_extractor.py`：新增 timeline 提取测试用例
