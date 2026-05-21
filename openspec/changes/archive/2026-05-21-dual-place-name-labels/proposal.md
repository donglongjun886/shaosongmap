## Why

当前地图标记仅显示古地名（如「汴京」），现代地名（如「河南开封」）只在点击 popup 后才可见。读者对照古今地名需要额外点击操作，尤其在看行军路线时反复 popup 体验较差。需要在标记上直接显示古今双标签，一目了然。

## What Changes

- 修改 `static/index.html` 中的地图渲染逻辑：地名标记从纯圆形改为「圆形图标 + 双行文字标签」，上行为古地名（较大字）、下行为现代地名（较小灰色字）
- 仅 CHGIS 精确匹配的地名显示双标签（有 modern_name），LLM 推断地名保持单行标签

## Capabilities

### New Capabilities
- `dual-place-labels`: 地图标记展示古今地名双标签，古名主标 + 今名副标

### Modified Capabilities
- `campaign-map-rendering`: 地名渲染方式从纯圆形标记改为圆形+文字双标签

## Impact

- `static/index.html`: **修改** — 地图图层配置（新增 symbol 标签层）
- 无后端变更、API 变更、依赖变更