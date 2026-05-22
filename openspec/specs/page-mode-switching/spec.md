# page-mode-switching Specification

## Purpose
TBD - created by archiving change page-interaction-redesign. Update Purpose after archive.
## Requirements
### Requirement: 输入模式

系统 SHALL 提供输入模式，作为页面的初始状态。输入模式下侧栏仅包含截图上传区和文本输入控件，地图以引导态占满右侧区域。

侧栏 MUST 包含：
- 截图拖拽上传区（含缩略图列表和批量识别控件）
- 文本输入框（textarea）
- 朝代选择下拉框
- 时间轴模式复选框
- 提交按钮

输入模式下的地图 MUST 以默认视图（中国全景，center [112, 33]，zoom 5）显示，不包含任何战役数据标记。

#### Scenario: 页面首次加载

- **WHEN** 用户首次打开页面
- **THEN** 页面处于输入模式，侧栏显示截图上传区和文本框，地图显示中国全景

#### Scenario: 用户填写文本并提交

- **WHEN** 用户在输入模式下粘贴文本、选择朝代、点击「生成地图」
- **THEN** 系统开始处理请求，显示分阶段进度条

### Requirement: 查看模式

系统 SHALL 提供查看模式，在提取成功后自动切换进入。查看模式下输入区折叠隐藏，侧栏展示结果面板和时间轴。

查看模式 MUST 包含：
- 「返回编辑」按钮（顶部）
- 尺度标签（tactical / battle / strategic）
- 可编辑结果面板（战役名、阵营、地名、路线、重新渲染按钮）
- 时间轴控件（如为 timeline 模式）
- 事件描述卡片（如为 timeline 模式）

#### Scenario: 提交成功后自动切换

- **WHEN** 后端返回完整的战役提取结果
- **THEN** 页面自动从输入模式切换到查看模式，地图 fitBounds 聚焦到战役数据范围

#### Scenario: 从查看模式返回编辑

- **WHEN** 用户在查看模式下点击「返回编辑」按钮
- **THEN** 页面切换回输入模式，文本框保留之前的内容，地图恢复引导态

### Requirement: 模式切换状态保持

系统 SHALL 在模式切换时保持关键状态不丢失。

切换规则 MUST 满足：
- 输入→查看：文本框内容保留，地图从引导态切换为结果态
- 查看→输入：`_lastExtractData` 保留（以便用户再次提交时无需重新提取）
- 用户在查看模式下对结果面板的编辑（修改地名/路线/阵营），返回输入模式时不自动清除

#### Scenario: 切换模式不丢失文本

- **WHEN** 用户在查看模式下点击「返回编辑」
- **THEN** 文本框仍显示之前输入的内容，用户可以直接修改后重新提交

#### Scenario: 重新提交后数据更新

- **WHEN** 用户返回输入模式、修改文本、再次提交
- **THEN** 新结果覆盖旧数据，页面再次切换到查看模式展示新地图

