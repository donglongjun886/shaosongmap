## MODIFIED Requirements

### Requirement: LLM 提取结构化数据

系统 SHALL 从战役文本中提取结构化 JSON，仅包含以下字段：
- `campaign_name`：战役名称
- `factions`：阵营信息（name、commanders、troops）
- `places`：地名列表（name、context、place_type）
- `routes`：行军路线（from、to、via）
- `units`：部队编制（name、faction、commander、troop_type、troop_count）

LLM 提示词 MUST 不包含 `events`、`unit_states`、`units.direction`、`scale` 字段及对应提取规则。

#### Scenario: 提取战役文本

- **WHEN** 输入包含行军路线和地名的战役文本
- **THEN** LLM 返回仅含地名、路线、阵营、部队编制的 JSON

## REMOVED Requirements

### Requirement: 时间轴事件提取
**Reason**: 不再需要时间轴模式
**Migration**: 删除 `extract_timeline()`、`_TIMELINE_SYSTEM_PROMPT`

### Requirement: 进攻方向提取
**Reason**: 静态地图不需要进攻箭头
**Migration**: 删除 `units.direction`、`unit_states.direction_target` 相关规则

### Requirement: Scale 分类
**Reason**: 仅保留一种地图模式
**Migration**: 删除 `scale` 字段及分类规则
