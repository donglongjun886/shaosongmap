## ADDED Requirements

### Requirement: 从战役文本提取时间线事件序列

系统 SHALL 在现有结构化提取基础上，将军事行动按时间顺序分解为事件序列 `events` 数组，每个事件包含序号、类型、描述、参与方和涉及的地名。

事件类型 MUST 为以下之一：`march`（行军）、`battle`（战斗）、`encamp`（扎营/驻扎）、`retreat`（撤退）。

每个事件 MUST 包含：
- `seq`: 从 1 开始的事件序号
- `event_type`: 事件类型（march / battle / encamp / retreat）
- `description`: 一句话中文描述，概括该事件的原文内容
- `actors`: 参与该事件的将领或部队名称列表
- `places_involved`: 该事件涉及的地名列表，MUST 为 `places` 数组中已出现的地名

事件序列 MUST 按文本中军事行动的**实际发生时间顺序**排列，而非原文叙述顺序。

#### Scenario: 成功提取行军→战斗→撤退序列

- **WHEN** 用户提交一段描述「A地出发→B地遭遇敌军→C地决战→敌军撤退」的战役文本
- **THEN** 系统返回 `events` 数组，依次包含 march、battle、retreat 类型事件，每个事件含对应地名和参与方

#### Scenario: 仅行军无战斗的文本

- **WHEN** 用户提交仅描述部队调动的文本（无战斗）
- **THEN** 系统返回的事件序列仅包含 march 和 encamp 类型，无 battle 或 retreat

#### Scenario: 事件地名与全局地名一致

- **WHEN** LLM 输出事件序列
- **THEN** 每个事件中的 `places_involved` 元素 MUST 出现在全局 `places` 数组中

#### Scenario: LLM 输出格式不合法（时间线模式）

- **WHEN** DeepSeek API 返回的 JSON 中 `events` 数组缺失或格式与 `TimelineEvent` 不匹配
- **THEN** 系统返回 422 错误，包含具体的校验失败信息