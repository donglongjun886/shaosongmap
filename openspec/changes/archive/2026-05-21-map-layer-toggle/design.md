## Context

当前 `static/index.html` 中地图初始化代码将地名标签渲染在单一 `place-labels` 符号层中，通过 MapLibre `format` 表达式将古名和今名拼接为双行文本。图例区域（`.legend`）为纯静态展示。用户无法独立控制古名/今名标签的显隐。

## Goals / Non-Goals

**Goals:**
- 将古地名和今地名对照拆分为两个独立的 MapLibre symbol 层
- 在图例区提供 checkbox 交互控件，可独立切换各图层可见性
- 图层切换即时生效，不影响已渲染的数据
- 标记圆点（CHGIS/LLM）始终可见，不受标签切换影响

**Non-Goals:**
- 不拆分 CHGIS 和 LLM 推断地名到独立图层
- 不控制圆点标记的可见性
- 不涉及行军路线图层的切换控制
- 不修改后端 API 或数据模型

## Decisions

### 决策 1：使用 MapLibre layout 属性控制可见性

**选择**：通过 `map.setLayoutProperty(layerId, 'visibility', 'visible'|'none')` 切换图层。

**备选方案**：通过 `filter` 表达式或操作数据源方式。
- `filter` 方式：需要修改数据源，且复选框联动复杂
- 数据源方式：需要维护两个独立数据源，增加数据同步开销
- `visibility` 方式：MapLibre 原生机制，不触发数据重新加载，性能最优，实现最简

### 决策 2：拆分出两个标签层而非保持单层

**选择**：创建 `place-labels-ancient` 和 `place-labels-modern` 两个独立层。

**备选方案**：保持单层，通过切换 `text-field` 表达式的条件逻辑。这会增加表达式复杂度，且无法独立控制偏移量，不如直接拆分清晰。

### 决策 3：今名标签层使用 filter 过滤空 modern_name

**选择**：`place-labels-modern` 层添加 `['!=', ['get', 'modern_name'], '']` 过滤条件。

这样 LLM 推断的无 modern_name 地名自动跳过今名层，无需在 JS 中额外处理。

### 决策 4：图例面板布局

**选择**：保留现有图例的 color dots 和样式信息，在下方新增 checkbox 控件区域。使用 `<label>` + `<input type="checkbox">` 实现，文字可点击。

## Risks / Trade-offs

- **古名/今名位置偏移**：因古名和今名现在分属两个独立层，`text-offset` 需分别设置（古名 `[0, 1.5]`，今名 `[0, 2.8]`）。当用户关闭古名但保留今名时，今名标签位置略低于原双行标签的视觉中心。→ 影响很小，属于可接受的 UI 细节。
- **层 ID 变更**：`place-labels` 更名为 `place-labels-ancient` 和 `place-labels-modern`。当前无其他代码引用 `place-labels` 层 ID，无破坏性影响。
