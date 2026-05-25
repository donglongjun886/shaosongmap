## ADDED Requirements

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
