## ADDED Requirements

### Requirement: CHGIS v6 古地名精确匹配

系统 SHALL 通过 CHGIS v6 数据集将古地名字符串匹配为经纬度坐标。

匹配逻辑 MUST：
- 以地名字符串在 CHGIS v6 地名表中做模糊查询
- 如能确定朝代上下文（从战役背景推断），按时间范围过滤候选结果
- 返回最佳匹配的经纬度坐标，并标注 `source: "chgis"`

#### Scenario: 精确匹配成功

- **WHEN** 输入地名「汴京」且 CHGIS v6 中存在该地名记录
- **THEN** 系统返回 `(114.35, 34.80)` 附近的坐标，`source` 字段为 `"chgis"`

#### Scenario: 同名多地按朝代消歧义

- **WHEN** 输入地名「安州」且 CHGIS 中存在多个同名候选
- **THEN** 系统根据文本上下文中的朝代信息过滤候选，返回对应朝代的坐标

#### Scenario: CHGIS 中不存在该地名

- **WHEN** 输入地名（如「鹰愁涧」这类虚构地名或极小地点）在 CHGIS v6 中无匹配
- **THEN** 系统标记该地名为未匹配，交由 LLM 推断兜底

### Requirement: LLM 上下文推断兜底

系统 SHALL 在 CHGIS 匹配失败时，调用 LLM 根据文本上下文推断地名的近似经纬度坐标。

LLM 推断 MUST：
- 接收完整战役文本和未能匹配的地名列作为输入
- 根据上下文中的已知地名、行军方向、山川河流关系推断近似坐标
- 返回坐标时标注 `source: "llm_infer"` 和可信度

#### Scenario: LLM 推断山川河流坐标

- **WHEN** 输入地名「汉水」（河流）无法在 CHGIS 中匹配
- **THEN** LLM 根据上下文中「襄阳」「渡汉水」推断汉水在襄阳附近的坐标段，`source` 为 `"llm_infer"`

#### Scenario: LLM 推断失败

- **WHEN** LLM 也无法推断某地名坐标（如完全无法判断位置的虚构地名）
- **THEN** 系统返回该地名为 `coordinates: null`，`source: "unknown"`

### Requirement: 所有坐标标注数据来源

系统 SHALL 为每个返回的坐标标注数据来源（`source` 字段），可选值包括 `chgis`、`llm_infer`、`unknown`。

#### Scenario: 前端根据来源区分展示

- **WHEN** 前端渲染地图标记
- **THEN** `chgis` 来源的标记使用实心图标，`llm_infer` 来源使用空心或半透明图标，`unknown` 来源不在地图上显示
