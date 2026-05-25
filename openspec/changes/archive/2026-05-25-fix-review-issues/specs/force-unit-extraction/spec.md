## MODIFIED Requirements

### Requirement: LLM 从战役文本提取部队实体

系统 SHALL 在 timeline 模式下从战役文本中识别独立的军事部队实体，每个部队 MUST 包含名称、所属阵营、指挥官、兵种、兵力描述和进攻方向。

`ForceUnit` 字段 MUST 包含：
- `name`: 部队名称（如「焦文通部」「合扎猛安」），在整个提取结果中 MUST 保持唯一
- `faction`: 所属阵营名称，MUST 对应 `factions` 数组中的某个 faction。阵营名 MUST 使用标准化称谓（如「宋」「金」），不得使用指代词
- `commander`: 指挥官姓名
- `troop_type`: 兵种类型，允许值：`infantry`（步兵）、`cavalry`（骑兵）、`mixed`（混合）
- `troop_count`: 兵力描述原文（如「数千」「满员一千骑」）
- `direction`: 进攻方向，MUST 为标准八方位词之一（东/南/西/北/东南/西南/东北/西北）。文本明确提及方向时直接使用；未明确但可根据战术语境推断时，MUST 尝试转换为标准方位词；完全无法推断时填 null

系统 MUST 能区分同一阵营下的多个独立行动部队（如宋军的「焦文通部」「郦琼部」「秦凤路兵马」是三个不同部队实体）。

#### Scenario: 成功提取多个部队实体

- **WHEN** 用户提交包含多个独立行动部队描述的战役文本（timeline 模式）
- **THEN** 系统返回 `units` 数组，包含每个部队的 name、faction、commander、troop_type、troop_count 和 direction

#### Scenario: 文本无明确部队实体

- **WHEN** 战役文本仅描述宏观战局，未提及独立部队名称
- **THEN** 系统返回空的 `units` 数组，不影响其他字段的正常提取

#### Scenario: 部队名称在文本中有别称

- **WHEN** 同一部队在文本不同位置以不同名称被提及（如「焦文通部」和「焦文通所部」）
- **THEN** LLM SHALL 使用统一的主名称，后处理 SHALL 通过编辑距离合并疑似同一部队的名称变体

#### Scenario: 文本明确提及进攻方向

- **WHEN** 战役文本明确写「完颜宗弼率军从岭北向南仰攻」
- **THEN** 该部队的 `direction` 字段为「南」

#### Scenario: 文本描述防守但无进攻方向

- **WHEN** 战役文本描述「王贵率三千步卒据守黄龙岭」，未提及该部队向何处运动
- **THEN** 该部队的 `direction` 字段为 null，因其处于防守状态无进攻方向

#### Scenario: 文本可推断方向

- **WHEN** 战役文本描述「自岭南迂回包抄」，虽未写明确切方位，但「包抄」隐含向敌方位置推进
- **THEN** LLM 根据上下文推断合理的方向方位词，填入 direction 字段

#### Scenario: direction 不得为模糊描述

- **WHEN** LLM 提取 direction 字段
- **THEN** 值 MUST 为东/南/西/北/东南/西南/东北/西北之一或 null，MUST NOT 为「侧翼」「塬底」「前方」等非方位词
