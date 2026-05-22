## ADDED Requirements

### Requirement: LLM 从战役文本提取部队实体

系统 SHALL 在 timeline 模式下从战役文本中识别独立的军事部队实体，每个部队 MUST 包含名称、所属阵营、指挥官、兵种和兵力描述。

`ForceUnit` 字段 MUST 包含：
- `name`: 部队名称（如「焦文通部」「合扎猛安」），在整个提取结果中 MUST 保持唯一
- `faction`: 所属阵营名称，MUST 对应 `factions` 数组中的某个 faction
- `commander`: 指挥官姓名
- `troop_type`: 兵种类型，允许值：`infantry`（步兵）、`cavalry`（骑兵）、`mixed`（混合）
- `troop_count`: 兵力描述原文（如「数千」「满员一千骑」）

系统 MUST 能区分同一阵营下的多个独立行动部队（如宋军的「焦文通部」「郦琼部」「秦凤路兵马」是三个不同部队实体）。

#### Scenario: 成功提取多个部队实体

- **WHEN** 用户提交包含多个独立行动部队描述的战役文本（timeline 模式）
- **THEN** 系统返回 `units` 数组，包含每个部队的 name、faction、commander、troop_type 和 troop_count

#### Scenario: 文本无明确部队实体

- **WHEN** 战役文本仅描述宏观战局，未提及独立部队名称
- **THEN** 系统返回空的 `units` 数组，不影响其他字段的正常提取

#### Scenario: 部队名称在文本中有别称

- **WHEN** 同一部队在文本不同位置以不同名称被提及（如「焦文通部」和「焦文通所部」）
- **THEN** LLM SHALL 使用统一的主名称，后处理 SHALL 通过编辑距离合并疑似同一部队的名称变体

### Requirement: LLM 提取部队时间状态

系统 SHALL 在 timeline 模式下为每个识别出的部队提取其在每个时间线步骤中的状态快照。

`UnitState` 字段 MUST 包含：
- `seq`: 对应的时间线步骤序号，MUST 为 `events` 数组中某个事件的 `seq` 值
- `unit_name`: 部队名称，MUST 对应 `units` 数组中某个 `ForceUnit` 的 `name`
- `status`: 部队状态，允许值：`deploying`（待命/列阵）、`marching`（进军/机动）、`engaging`（交战/接敌）、`routing`（溃散/败退）
- `location`: 部队当前位置关联的地名，MUST 为 `places` 数组中的某个地名；当部队位置无法关联到具体地名时可为 null
- `description`: 一句话中文描述，概括该部队在此步骤的战术动作（如「焦文通部转向娄室中军，意图从侧翼压上」）

`unit_states` 数组 SHALL 包含所有部队在所有步骤中的状态记录。并非每个部队都需要在每个步骤有状态记录——仅在文本描述了该部队在该步骤的行为时才需记录。

#### Scenario: 部队状态跨事件追踪

- **WHEN** 战役文本描述了同一部队在多个时间步骤中的连续行动（如焦文通部：待命→转向→侧翼包抄→遭遇骑兵冲击→溃散）
- **THEN** `unit_states` 数组包含该部队在不同 `seq` 下的多条状态记录，每条状态正确反映当前步骤的部队状况

#### Scenario: 部队在某步骤无描述

- **WHEN** 文本未描述某部队在某步骤的行为
- **THEN** 该部队在该步骤可以没有对应的 `UnitState` 记录；前端渲染时沿用上一已知状态

#### Scenario: 部队状态与事件不同步

- **WHEN** LLM 输出的 `UnitState.seq` 在 `events` 数组中不存在
- **THEN** 后处理校验丢弃该条状态记录，并记录警告日志

### Requirement: 部队兵力类型识别

系统 SHALL 根据文本描述判断部队的兵种类型。

判断规则：
- 文本明确提及「骑」「铁浮屠」「合扎猛安」「拐子马」等骑兵相关词汇 → `cavalry`
- 文本明确提及「步」「弩手」「刀斧手」「盾兵」等步兵相关词汇 → `infantry`
- 包含多种兵种或无法判断 → `mixed`

#### Scenario: 文本明确描述骑兵

- **WHEN** 战役文本描述「一千骑，人马俱甲，宛如铁浮屠」
- **THEN** 该部队的 `troop_type` 为 `cavalry`

#### Scenario: 文本未提及兵种

- **WHEN** 战役文本仅提及部队名称和人数，未描述兵种特征
- **THEN** 该部队的 `troop_type` 可为 `mixed` 或根据上下文合理推断