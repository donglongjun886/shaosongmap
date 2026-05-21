## MODIFIED Requirements

### Requirement: 从战役文本提取结构化数据

系统 SHALL 接收一段中文战役/行军文本，通过 DeepSeek API 提取结构化信息，并返回经过 Pydantic 校验的 JSON 对象。

提取的字段 MUST 包含：
- `campaign_name`: 战役名称（可为 null）
- `factions`: 参战方列表，每方包含名称、将领列表、兵力描述
- `places`: 地名出现列表，按文中出现顺序排列
- `routes`: 行军路线列表，每条包含起点、终点、途经地点
- `events`: 事件序列列表（timeline 模式），按时间顺序排列的军事行动事件。每个事件 MUST 包含序号（`seq`）、事件类型（`event_type`: march / battle / encamp / retreat）、中文描述（`description`）、参与方（`actors`）、涉及地名（`places_involved`）。事件涉及的地名 MUST 出现在全局 `places` 数组中。当用户请求 timeline 模式时 MUST 返回；static 模式时可为空数组。

系统 MUST 能区分文本中的实际军事行动和人物对话/议论内容。人物言论中假设、建议或讨论的军事行动（如「臣以为应从X出兵」）MUST NOT 被视为实际行军节点。朝堂对话和场景描写段落 MUST 被忽略，仅从军事行动描述段落中提取信息。**事件序列中的事件同样 MUST 仅来源于实际军事行动，对话中的假设行动不可成为事件。**

#### Scenario: 成功提取完整战役信息

- **WHEN** 用户提交一段包含双方将领、兵力、地名和行军路线的战役文本
- **THEN** 系统返回包含 `campaign_name`、`factions`（至少两方）、`places`（至少三个地名）、`routes`（至少一条路线）的结构化 JSON

#### Scenario: 文本中只包含行军不包含战斗

- **WHEN** 用户提交仅描述行军路线（无战斗）的文本
- **THEN** 系统仍然返回结构化 JSON，其中 `campaign_name` 为 null，`places` 和 `routes` 正常填充

#### Scenario: 文本混合朝堂对话和军事行动

- **WHEN** 用户提交的文本包含朝堂对话（如「臣以为应从襄阳出兵」）和实际军事行动（如「岳飞率军自襄阳出发」）
- **THEN** 系统仅从实际军事行动段落提取地名和路线，忽略对话中的假设性军事建议

#### Scenario: 文本无实际军事行动

- **WHEN** 用户提交的文本全部为朝堂对话或场景描写，没有任何确认的军事行动
- **THEN** 系统返回空的 `places` 和 `routes` 数组，`campaign_name` 为 null

#### Scenario: LLM 输出格式不合法

- **WHEN** DeepSeek API 返回的 JSON 与 Pydantic 模型不匹配（缺少必填字段、类型错误）
- **THEN** 系统返回 422 错误，包含具体的校验失败信息

#### Scenario: 时间线模式提取事件序列

- **WHEN** 用户在 timeline 模式下提交包含时序军事行动的战役文本
- **THEN** 系统返回的 `events` 数组包含按时间顺序排列的事件，每个事件有正确的 `event_type`、`description`、`actors` 和 `places_involved`

## ADDED Requirements

### Requirement: 时间线模式提取开关

系统 SHALL 支持通过参数切换提取模式：`mode="timeline"` 时启用事件序列提取，`mode="static"`（默认）时仅提取静态结构。

#### Scenario: timeline 模式显式请求

- **WHEN** 请求中 `mode` 字段为 `"timeline"`
- **THEN** 系统调用 `extract_timeline()` 函数，返回包含 `events` 数组的结果

#### Scenario: 默认 static 模式

- **WHEN** 请求中未指定 `mode` 字段或指定为 `"static"`
- **THEN** 系统调用 `extract()` 函数，`events` 为空数组，行为与当前版本一致
