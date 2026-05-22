## Why

当前系统从战役文本中提取的是「地理信息」（地名坐标、行军路线），但《绍宋》等小说中的战役段落核心是「战术动态」——部队转向、侧翼包抄、骑兵冲击、全线崩溃。这些激烈的战术动作被压缩在同一两个地理标记点周围，地图上只能看到静止的点和线，完全丢失了战役的戏剧性和空间叙事。需要让系统理解「谁在哪里做了什么、结果如何」，并把这种战术动态在时间线上可视化。

## What Changes

- **新增 `ForceUnit` 和 `UnitState` 数据模型**：部队成为一等实体，有名称、阵营、兵种、兵力，并在每个时间线步骤拥有独立状态（待命/进军/交战/溃散）
- **新增部队提取能力**：LLM 从战役文本中识别独立部队实体，追踪同一部队跨事件的状态变化，输出结构化的部队+状态数据
- **新增部队地图可视化**：在地图上以抽象色块+标签展示部队位置，按阵营着色，按状态切换样式（进军=实心/溃散=破碎），支持模糊区域表达（不追求精确坐标）
- **新增战术动作动画模型**：路径动画（部队沿路线移动）、生长动画（进军路线逐步展开）、显隐动画（部队出现/消失）、属性动画（颜色/大小渐变表示状态切换）
- **时间线集成**：部队状态挂载在现有时间线系统上，逐帧推进时部队标记自动更新位置和样式
- **扩展提取 API 响应**：`/api/extract` 的 SSE 结果事件中新增 `units` 和 `unit_states` 字段

## Capabilities

### New Capabilities

- `force-unit-extraction`: LLM 从战役文本中提取独立部队实体，识别每个部队在时间线各步骤中的位置、状态和战术动作
- `force-unit-visualization`: 地图上以抽象色块渲染部队标记，支持阵营着色、状态切换样式、战术动作动画（路径/生长/显隐/属性），由时间线步进驱动更新

### Modified Capabilities

- `campaign-text-extraction`: 提取结果新增 `units`（部队列表）和 `unit_states`（每步状态）字段；部队信息在 timeline 模式下提取，static 模式下可为空
- `campaign-map-rendering`: 地图新增部队标记图层和战术动画图层；时间线过滤机制扩展至部队标记（按 step 显隐）；图例区新增部队图层切换

## Impact

- `shaosongmap/models.py`: 新增 `ForceUnit`、`UnitState`、`UnitStatus`、`TacticalAction` 等 Pydantic 模型；`CampaignTimeline` 新增 `units` 和 `unit_states` 字段
- `shaosongmap/extractor.py`: 新增 `_FORCE_UNIT_SYSTEM_PROMPT` 或扩展现有 prompt；新增部队提取函数；新增部队状态后处理校验
- `app.py`: SSE result 事件新增 units/unit_states 数据；GeoJSON 构建新增部队标记 Feature
- `static/index.html`: 新增部队标记 MapLibre 图层（符号层+标签层）；新增战术动画管理模块；时间线步进函数扩展部队状态更新；新增部队状态卡片 UI