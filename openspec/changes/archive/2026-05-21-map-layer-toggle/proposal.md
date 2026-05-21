## Why

当前地图将所有地名标签（古地名+今地名对照）渲染在单一文字层中，读者无法按需关闭某个标签层。当用户熟悉某地区现代地理时，今地名对照会造成视觉干扰；当用户只想关注古今对照时，也无法单独突出今名。需要将古/今地名标签拆分为独立图层，并在图例区提供交互式开关。

## What Changes

- **拆分地图标签层**：将现有的 `place-labels` 符号层拆分为 `place-labels-ancient`（古地名深色粗体）和 `place-labels-modern`（今地名灰色斜体）两个独立图层
- **图例区升级为图层控制面板**：在现有图例区增加 checkbox 交互控件，可独立切换古地名标签和今地名标签的显隐
- 标记圆点（CHGIS/LLM）不受图层切换影响，始终可见
- 弹窗 popup 行为不变
- 行军路线层保持不动

## Capabilities

### New Capabilities

- `map-layer-control`: 地图图层交互式控制——用户可在地图图例区通过 checkbox 开关独立控制古地名标签层和今地名标签层的可见性

### Modified Capabilities

- `campaign-map-rendering`: 地图标签渲染方式变更——从单一双行标签层拆分为两个独立符号层，图层可见性通过 layout visibility 控制

## Impact

- 仅修改 `static/index.html`（前端单文件，约 30-40 行增删）
- 后端 API、数据模型、GeoJSON 结构均不受影响
- 不影响现有测试