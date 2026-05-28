# Timeline Interaction UI 时间轴交互控件 (Delta)

## MODIFIED Requirements

### Requirement: 时间轴进度条

系统 SHALL 在查看模式侧栏渲染时间轴进度条（React `Timeline` 组件），取代 vanilla JS DOM 操作实现。

进度条 MUST 保留所有现有行为：
- 按事件序号排列的节点（圆点），已完成填充实心、未完成空心
- 当前事件节点高亮
- 节点间连接线（已完成实线、未完成虚线）
- 仅在查看模式下可见

新增行为：
- 节点 hover 显示事件简要 tooltip
- 当前步骤节点带脉冲动画（CSS `@keyframes pulse`）

#### Scenario: 初始加载显示完整进度条

- **WHEN** 后端返回包含 8 个事件的战役时间线
- **THEN** 查看模式下 Timeline 组件显示 8 个节点，当前步为最后一步，所有节点为已完成状态

#### Scenario: 步进后进度条更新

- **WHEN** 用户点击「上一步」从步骤 5 回到步骤 4
- **THEN** React 状态更新触发 Timeline 重渲染：节点 1-4 已完成，节点 5-8 未完成，节点 4 高亮

### Requirement: 步进按钮控制

系统 SHALL 在 Timeline 组件中提供「上一步」和「下一步」按钮，通过事件总线通知 Canvas 渲染器更新地图。

按钮行为 MUST 保留所有现有逻辑：
- 初始状态当前步为最后一步，「下一步」禁用
- 当前步为第 1 步时，「上一步」禁用
- 点击时触发 `eventBus.emit('timeline:step', { step })`

新增行为：
- 支持键盘左右箭头快捷键（全局监听，时间轴区域 focus 时生效）
- 播放/暂停按钮：自动每 2 秒推进一步，到达最后一步停止

#### Scenario: 逐步前进查看战役

- **WHEN** 用户连续点击 3 次「上一步」
- **THEN** 通过事件总线发送 3 次 `timeline:step`，Canvas 渲染器每次收到后更新地图

#### Scenario: 键盘左右箭头切换

- **WHEN** 用户按下右箭头键且未在输入框中
- **THEN** 当前步骤 +1，效果与点击「下一步」相同

### Requirement: 事件描述卡片

系统 SHALL 在 Timeline 组件中渲染当前事件的描述卡片（React `EventCard` 子组件）。

卡片 MUST 保留所有现有内容：
- 事件序号和类型中文标签
- 事件描述文本
- 涉及的将领/部队
- 涉及的地名列表

#### Scenario: 步进时事件卡片同步更新

- **WHEN** 用户点击「下一步」从事件 2 推进到事件 3
- **THEN** React 状态更新触发 EventCard 重渲染为事件 3 的内容

### Requirement: 地图增量渲染

系统 SHALL 根据当前步进状态通过事件总线通知 MapLibre 和 Canvas 渲染器增量更新。

渲染规则保留所有现有行为：
- 初始加载显示完整地图
- 推进到第 N 步时，仅显示 seq ≤ N 的路线段和高亮地名
- 回退时隐藏 seq > N 的路线段

新增行为：
- 步骤切换时，Canvas 渲染器执行部队状态过渡动画（生长/脉冲/碎裂）

#### Scenario: 路线动态生长

- **WHEN** 用户从第 2 步推进到第 3 步，且第 3 步事件包含新路线段「唐州→蔡州」
- **THEN** MapLibre 显示新路线段，Canvas 无变化（路线仍在 MapLibre line layer 中）

#### Scenario: 部队状态动画

- **WHEN** 用户推进到步骤 4，合扎猛安首次出现
- **THEN** Canvas 渲染器执行箭头生长动画（600ms）+ 兵牌 opacity 渐变
