## ADDED Requirements

### Requirement: 古地名标签图层独立控制

系统 SHALL 在地图图例区提供「古地名」checkbox 控件，用户可通过该控件独立切换古地名标签层的可见性。关闭该图层时，古地名文字标签隐藏，但地名标记圆点（CHGIS 绿色实心 / LLM 黄色虚线）不受影响、继续显示。

#### Scenario: 隐藏古地名标签

- **WHEN** 用户取消勾选图例区「古地名」checkbox
- **THEN** 地图上所有地名标记的古名文字标签（深色粗体）立即隐藏，标记圆点仍然可见

#### Scenario: 重新显示古地名标签

- **WHEN** 用户重新勾选图例区「古地名」checkbox
- **THEN** 地图上所有地名标记的古名文字标签立即恢复显示

#### Scenario: 重新渲染后图层状态保持

- **WHEN** 用户调整图层开关后点击「重新渲染」
- **THEN** 地图数据更新后各图层可见性状态不变（开关状态保持用户设置）

### Requirement: 今地名标签图层独立控制

系统 SHALL 在地图图例区提供「今地名对照」checkbox 控件，用户可通过该控件独立切换今地名标签层的可见性。仅对有 modern_name 的地名（CHGIS 精确匹配）生效，LLM 推断且无 modern_name 的地名不受此开关影响。

#### Scenario: 隐藏今地名对照标签

- **WHEN** 用户取消勾选图例区「今地名对照」checkbox
- **THEN** 地图上所有灰色斜体现代地名标签立即隐藏，古名标签保持显示

#### Scenario: 重新显示今地名对照标签

- **WHEN** 用户重新勾选图例区「今地名对照」checkbox
- **THEN** 地图上所有有现代名的地名标记下方恢复显示灰色斜体今名标签

#### Scenario: 今名开关对无现代名地名无影响

- **WHEN** 地图包含 LLM 推断地名（无 modern_name）且用户切换「今地名对照」checkbox
- **THEN** 那些 LLM 推断地名的坐标位置不出现任何今名标签

### Requirement: 图层控制面板 UI

系统 SHALL 在现有地图图例区域（`.legend`）中扩展图层控制面板，包含 checkbox 控件和描述标签。控件 MUST 支持点击文字标签切换状态（使用 `<label>` 元素）。

#### Scenario: 图层控件初始状态

- **WHEN** 页面加载完成
- **THEN** 「古地名」和「今地名对照」checkbox 均默认勾选，对应图层均可见

#### Scenario: 点击文字切换

- **WHEN** 用户点击 checkbox 旁边的描述文字（如「古地名 (深色粗体)」）
- **THEN** checkbox 状态切换，对应图层可见性随之变化
