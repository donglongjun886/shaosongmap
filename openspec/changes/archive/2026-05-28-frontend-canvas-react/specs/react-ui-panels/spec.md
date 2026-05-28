# React UI Panels 组件化面板

## Purpose

React 18 替换 vanilla JS DOM 操作，组件化管理时间轴、图例、工具栏、部队列表等 UI 面板。通过事件总线与 Canvas 渲染器解耦通信。

## ADDED Requirements

### Requirement: React 18 挂载与隔离

系统 SHALL 将 React 18 挂载到独立 DOM 容器中，不接管地图容器和 Canvas 覆盖层。

React 根节点 MUST：
- 挂载到 `#react-ui` 容器（位于地图容器之外）
- 使用 `createRoot` API（React 18 并发模式）
- 仅在 P2 阶段激活，P0/P1 阶段保持 vanilla JS UI

#### Scenario: React UI 不影响地图渲染

- **WHEN** React 组件重新渲染（如时间轴状态更新）
- **THEN** 地图 Canvas 和 MapLibre 不触发不必要的重绘

### Requirement: 时间轴组件

系统 SHALL 将时间轴面板实现为 React `Timeline` 组件，管理步骤切换、播放/暂停、步骤高亮。

Timeline 组件 MUST：
- 接收 `steps: TimelineStep[]` 和 `currentStep: number` 作为 props
- 点击步骤按钮时通过事件总线 `emit('timeline:step', { step })` 通知 Canvas 渲染器
- 支持键盘左右箭头切换步骤
- 播放模式：自动每 2 秒推进步骤（可暂停）
- 当前步骤高亮显示（蓝色边框 + 背景加深）

#### Scenario: 点击步骤切换

- **WHEN** 用户点击时间轴步骤 3 按钮
- **THEN** Timeline 组件 `emit('timeline:step', { step: 3 })`，Canvas 渲染器收到后更新部队状态

#### Scenario: 键盘切换步骤

- **WHEN** 用户按下右箭头键且时间轴未在播放
- **THEN** 当前步骤 +1，触发与点击相同的步骤切换逻辑

#### Scenario: 自动播放

- **WHEN** 用户点击播放按钮
- **THEN** 每 2 秒自动推进 1 步，到达最后一步后停止

### Requirement: 图例组件

系统 SHALL 将图例面板实现为 React `Legend` 组件，管理各图层的显示/隐藏 checkbox。

Legend 组件 MUST：
- 动态生成图层条目（基于当前渲染的图层列表）
- 每个条目包含：checkbox + 图层名称 + 颜色预览色块
- checkbox 状态变化时 `emit('layer:toggle', { layerId, visible })`
- 图层列表：地名标记（古/今）、行军路线、部队兵牌、地形色块

#### Scenario: 隐藏部队图层

- **WHEN** 用户取消勾选图例中的「部队兵牌」checkbox
- **THEN** Legend 组件 `emit('layer:toggle', { layerId: 'units', visible: false })`，Canvas 渲染器停止绘制兵牌和箭头

### Requirement: 工具栏组件

系统 SHALL 将工具栏实现为 React `Toolbar` 组件。

Toolbar 组件 MUST 包含：
- 缩放按钮（+/-），调用 `map.zoomIn()` / `map.zoomOut()`
- 复位按钮，调用 `map.fitBounds()` 回到数据范围
- 主题切换按钮（当前仅 comic 主题）
- 截图按钮（导出当前 Canvas + MapLibre 为 PNG）

#### Scenario: 截图导出

- **WHEN** 用户点击截图按钮
- **THEN** 系统合并 MapLibre canvas 和 Canvas 覆盖层为一张 PNG 并触发下载

### Requirement: 部队列表组件

系统 SHALL 将部队状态列表实现为 React `UnitList` 组件，显示当前步骤所有部队信息。

UnitList 组件 MUST：
- 接收 `units: UnitState[]` 作为 props（从事件总线订阅 `data:update` 获取）
- 每行显示：阵营色圆点 + 部队名称 + 状态中文标签 + 兵力数
- 点击部队行时 `emit('unit:focus', { unitName })`，Canvas 高亮该部队
- 空状态显示「当前步骤无部队动态信息」

#### Scenario: 部队列表跟随步骤更新

- **WHEN** 用户切换到步骤 3
- **THEN** UnitList 组件通过事件总线接收到新的 units 数据，自动更新显示

#### Scenario: 点击部队高亮地图

- **WHEN** 用户点击 UnitList 中的「焦文通部」
- **THEN** Canvas 渲染器将该部队兵牌放大 1.2 倍并增加金色光晕

### Requirement: 事件总线

系统 SHALL 使用 `EventTarget` 实现轻量事件总线，作为 React UI 和 Canvas 渲染器之间的唯一通信通道。

事件总线 MUST：
- 定义标准事件名：`timeline:step`, `layer:toggle`, `unit:focus`, `data:update`, `render:done`
- 所有跨模块通信通过事件总线，禁止直接引用对方模块
- 事件 payload 使用简单 JSON 可序列化对象

#### Scenario: UI 和 Canvas 解耦

- **WHEN** Canvas 渲染器模块缺失或加载失败
- **THEN** React UI 面板仍可正常渲染和交互（时间轴可点击，只是地图不响应）
