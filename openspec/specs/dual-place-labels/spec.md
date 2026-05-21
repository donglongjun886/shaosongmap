## Requirements

### Requirement: 古今地名双标签

系统 SHALL 在地图上为每个 CHGIS 精确匹配的地名标记显示双行文字标签：第一行为古地名（深色粗体）、第二行为现代地名（灰色斜体）。LLM 推断且无 modern_name 的地名保持单行标签。

双标签 MUST：
- 古名使用深色（#1a1a1a）粗体，今名使用灰色（#888888）斜体
- 标签定位在地名标记圆点下方
- 不改动 popup 弹窗内容

#### Scenario: CHGIS 地名显示双标签

- **WHEN** 地图渲染一个 CHGIS 精确匹配的地名（如「汴京」，modern_name 为「河南开封」）
- **THEN** 标记下方显示两行文字：上方深色粗体「汴京」、下方灰色斜体「河南开封」

#### Scenario: LLM 推断地名显示单标签

- **WHEN** 地图渲染一个 LLM 推断地名（无 modern_name）
- **THEN** 标记下方仅显示一行古地名文字

#### Scenario: Popup 内容不变

- **WHEN** 用户点击地名标记
- **THEN** popup 弹窗仍然显示地名、来源和古今对照（如有），与现有行为一致
