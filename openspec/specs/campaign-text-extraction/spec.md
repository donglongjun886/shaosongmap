## Requirements

### Requirement: 从战役文本提取结构化数据

系统 SHALL 接收一段中文战役/行军文本，通过 DeepSeek API 提取结构化信息，并返回经过 Pydantic 校验的 JSON 对象。

System Prompt SHALL 精简至最小必要指令，移除 JSON schema 中的注释行和冗余示例，减少每次 API 调用的输入 token 消耗。Prompt 语义和提取要求保持不变。

提取的字段 MUST 包含：
- `campaign_name`: 战役名称（可为 null）
- `factions`: 参战方列表，每方包含名称、将领列表、兵力描述
- `places`: 地名出现列表，按文中出现顺序排列
- `routes`: 行军路线列表，每条包含起点、终点、途经地点
- `events`: 事件序列列表（timeline 模式），按时间顺序排列的军事行动事件。每个事件 MUST 包含序号（`seq`）、事件类型（`event_type`: march / battle / encamp / retreat）、中文描述（`description`）、参与方（`actors`）、涉及地名（`places_involved`）。事件涉及的地名 MUST 出现在全局 `places` 数组中。当用户请求 timeline 模式时 MUST 返回；static 模式时可为空数组。
- `units`: 部队实体列表（timeline 模式），从文本中识别出的独立军事部队。每个部队 MUST 包含名称（`name`）、所属阵营（`faction`）、指挥官（`commander`）、兵种类型（`troop_type`: infantry / cavalry / mixed）和兵力描述（`troop_count`）。当用户请求 timeline 模式时 MUST 返回；static 模式时可为空数组。
- `unit_states`: 部队状态列表（timeline 模式），记录各部队在各时间线步骤中的状态快照。每条状态 MUST 包含步骤序号（`seq`）、部队名称（`unit_name`，MUST 对应 units 中的某个 ForceUnit）、状态（`status`: deploying / marching / engaging / routing）、位置关联地名（`location`，MUST 为 places 中的地名或 null）和中文描述（`description`）。当用户请求 timeline 模式时 MUST 返回；static 模式时可为空数组。

系统 MUST 能区分文本中的实际军事行动和人物对话/议论内容。人物言论中假设、建议或讨论的军事行动（如「臣以为应从X出兵」）MUST NOT 被视为实际行军节点。朝堂对话和场景描写段落 MUST 被忽略，仅从军事行动描述段落中提取信息。事件序列中的事件同样 MUST 仅来源于实际军事行动，对话中的假设行动不可成为事件。部队实体和部队状态同样 MUST 仅来源于实际军事行动中的部队描述。

系统 MUST 能区分独立地名和作为军队编制名称修饰语的地名。当地名作为军队编制名称的一部分出现时（如「秦凤路大军」中的「秦凤路」、「泾原路兵马」中的「泾原路」），该地名 MUST NOT 被提取为 places。仅当该地名在文中也作为独立地理实体被提及时（如「大军自秦凤路出发」中的「秦凤路」），才可将其提取为 places。

系统 SHALL 对 LLM 返回的 places 列表进行后处理过滤：若某地名的 `context` 字段中该地名后紧跟军队编制后缀（军、大军、兵马、部队、将士、诸军、各部、行营、都统司等），则 MUST 从 places 列表中移除，除非同一地名在文中其他位置作为独立地理位置出现。

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

#### Scenario: 军队编制名中的地名不被提取

- **WHEN** 用户提交的文本中包含军队编制名如「秦凤路大军」「泾原路兵马」
- **THEN** 系统 MUST NOT 将「秦凤路」「泾原路」提取为 places 列表中的条目，除非这些地名在文中其他位置作为独立地理实体出现

#### Scenario: 后处理过滤军队编制名

- **WHEN** LLM 返回的 places 中某地名的 context 字段显示该地名后紧跟军队编制后缀（如「秦凤路大军自渭州出发」）
- **THEN** 后处理过滤函数 MUST 从 places 列表中移除该条目，同时保留同一地名的其他独立出现（如文末「秦凤路境内」）

#### Scenario: 时间线模式提取部队和状态

- **WHEN** 用户在 timeline 模式下提交包含部队描述的战役文本
- **THEN** 系统返回的 `units` 数组包含识别出的部队实体，`unit_states` 数组包含各部队在各步骤的状态快照

#### Scenario: static 模式不提取部队数据

- **WHEN** 用户在 static 模式下提交战役文本
- **THEN** 系统返回的 `units` 和 `unit_states` 为空数组，行为与当前版本兼容

### Requirement: 提取结果包含数据来源标记

系统 SHALL 在提取结果中保留原始文本片段，供后续 Geocoder 和前端引用。

#### Scenario: 地名与原文关联

- **WHEN** 系统提取地名列表
- **THEN** 每个地名 MUST 附带其在原文中的位置或上下文片段，供 Geocoder 消歧义使用

### Requirement: 时间线模式提取开关

系统 SHALL 支持通过参数切换提取模式：`mode="timeline"` 时启用事件序列提取，`mode="static"`（默认）时仅提取静态结构。

#### Scenario: timeline 模式显式请求

- **WHEN** 请求中 `mode` 字段为 `"timeline"`
- **THEN** 系统调用 `extract_timeline()` 函数，返回包含 `events` 数组的结果

#### Scenario: 默认 static 模式

- **WHEN** 请求中未指定 `mode` 字段或指定为 `"static"`
- **THEN** 系统调用 `extract()` 函数，`events` 为空数组，行为与当前版本一致

### Requirement: 地名类型标记

Place 模型 SHALL 包含可选的 `place_type` 字段，用于标记地名的地理类型。

`place_type` 的允许值 MUST 包括：
- `city`: 城池、城镇
- `mountain_pass`: 关隘、山口
- `river`: 河流、水系
- `mountain`: 山脉、山岭
- `region`: 行政区、区域（如路、州、府）
- `battlefield`: 战场、交战地点

`place_type` 为 Optional，当 LLM 无法确定类型时可为 null。该字段 SHALL 在 Prompt 中引导 LLM 输出，但不强制。后处理 MUST 不依赖该字段。

#### Scenario: LLM 输出地名类型

- **WHEN** LLM 能够从上下文判断地名类型（如「潼关」→ mountain_pass、「渭水」→ river）
- **THEN** 返回的 Place 对象中 `place_type` 字段为对应枚举值

#### Scenario: LLM 无法确定地名类型

- **WHEN** LLM 无法从上下文确定地名类型
- **THEN** Place 对象中 `place_type` 字段为 null，不影响其他字段的提取

### Requirement: LLM 识别并标准化阵营归属

系统 SHALL 在提取 prompt 中引导 LLM 从历史语境推断并标准化阵营（faction）名称，确保 ForceUnit.faction 与 factions[].name 精确匹配。

阵营识别 MUST 遵循以下优先级：
1. 优先使用文本中明确提及的阵营名（如「宋军」「金兵」「西夏军」）
2. 若文本未明确命名阵营，MUST 根据历史常识推断：宋代历史语境下，正方/主角方为「宋」，敌方为「金」或「西夏」或「辽」
3. faction 名称 MUST 使用标准历史称谓（「宋」「金」「西夏」「辽」「蒙古」等单字朝代名），不得使用「我军」「敌军」「对方」等指代词
4. ForceUnit.faction 字段 MUST 与 factions 数组中某个 faction 的 name 字段精确匹配（字符串完全一致）

#### Scenario: 文本明确提及阵营名

- **WHEN** 战役文本中包含「宋军」「金军」等明确的阵营指称
- **THEN** LLM 直接使用「宋」「金」作为 factions 的 name，ForceUnit.faction 与之一致

#### Scenario: 文本未提及阵营名但可从历史语境推断

- **WHEN** 战役文本仅提将领名（如「王贵」「完颜宗弼」）和部队名，未明确写「宋军」「金军」
- **THEN** LLM MUST 根据宋代历史常识推断：王贵、张宪等为宋方，完颜宗弼、合扎猛安等为金方，faction 名分别标准化为「宋」和「金」

#### Scenario: 阵营名不使用指代词

- **WHEN** LLM 提取 faction 字段
- **THEN** faction 值 MUST 为「宋」「金」「西夏」等标准称谓，MUST NOT 为「我军」「敌方」「对方」等指代词

### Requirement: 阵营色驱动的可视化一致性

系统 SHALL 通过标准化阵营名保证前端阵营色映射的正确性。

前端阵营色映射表：
- faction 含「宋」→ 靛蓝 `#2b4c7e`（`--faction-song`）
- faction 含「金」→ 朱砂红 `#c23b22`（`--faction-jin`）
- 其他/未知 → 墨色 `#2c2c2c`（`--faction-unknown`）

LLM MUST 输出精确的阵营名，确保前端 `_factionColor()` 函数能正确匹配。若 faction 值为「金军」「金兵」，前端 `indexOf('金')` 仍可匹配；若 faction 值为「敌军」，则匹配失败，标记显示为未知阵营色。

#### Scenario: 宋军部队使用蓝色标记

- **WHEN** LLM 输出的 ForceUnit.faction 值为「宋」，前端渲染
- **THEN** 部队旗帜/标记使用靛蓝色 `#2b4c7e`

#### Scenario: 金军部队使用红色标记

- **WHEN** LLM 输出的 ForceUnit.faction 值为「金」，前端渲染
- **THEN** 部队旗帜/标记使用朱砂红 `#c23b22`

#### Scenario: 阵营名不匹配时回退

- **WHEN** LLM 输出的 faction 值不含「宋」也不含「金」（如纯「敌方」）
- **THEN** 前端 `_factionColor()` 返回墨色 `#2c2c2c`，不影响渲染
