## MODIFIED Requirements

### Requirement: 从战役文本提取结构化数据

系统 SHALL 接收一段中文战役/行军文本，通过 DeepSeek API 提取结构化信息，并返回经过 Pydantic 校验的 JSON 对象。

System Prompt SHALL 精简至最小必要指令，移除 JSON schema 中的注释行和冗余示例，减少每次 API 调用的输入 token 消耗。Prompt 语义和提取要求保持不变。

#### Scenario: 精简 Prompt 提取结果一致

- **WHEN** 使用精简后的 System Prompt 提取战役文本
- **THEN** 提取结果的结构、字段和质量与精简前保持一致
