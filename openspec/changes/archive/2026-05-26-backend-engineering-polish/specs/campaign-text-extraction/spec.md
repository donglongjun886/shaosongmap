## MODIFIED Requirements

### Requirement: 地名类型标记

Place 模型 SHALL 包含可选的 `place_type` 字段，用于标记地名的地理类型。

`place_type` 的允许值 MUST 包括：
- `city`: 城池、城镇
- `mountain_pass`: 关隘、山口
- `river`: 河流、水系
- `mountain`: 山脉、山岭
- `region`: 行政区、区域（如路、州、府）
- `battlefield`: 战场、交战地点
- `camp`: 营寨、扎营地

`place_type` 为 Optional，当 LLM 无法确定类型时可为 null。该字段 SHALL 在 Prompt 中引导 LLM 输出，但不强制。后处理 MUST 不依赖该字段。

#### Scenario: LLM 输出地名类型

- **WHEN** LLM 能够从上下文判断地名类型（如「潼关」→ mountain_pass、「渭水」→ river）
- **THEN** 返回的 Place 对象中 `place_type` 字段为对应枚举值

#### Scenario: LLM 无法确定地名类型

- **WHEN** LLM 无法从上下文确定地名类型
- **THEN** Place 对象中 `place_type` 字段为 null，不影响其他字段的提取

#### Scenario: 营寨类型地名

- **WHEN** 战役文本中出现营寨类地名（如「金军营寨」「宋军大营」「临时营地」）
- **THEN** LLM 输出 `place_type` 为 `camp`