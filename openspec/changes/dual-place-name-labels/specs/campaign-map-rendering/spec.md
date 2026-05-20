## MODIFIED Requirements

### Requirement: 交互式地图渲染

系统 SHALL 使用 MapLibre GL JS 在浏览器中渲染交互式地图，底图使用 OpenStreetMap 瓦片。

地图 MUST 支持：
- 鼠标缩放（+/-）和拖拽平移
- 按 `source` 字段区分地名标记样式（实心=CHGIS，空心=LLM 推断）
- **CHGIS 精确匹配的地名标记显示双行标签**（古名深色粗体 + 今名灰色斜体），**LLM 推断地名标记显示单行标签**
- 行军路线以带箭头线条展示
- 每条路线可独立显示/隐藏

#### Scenario: 地图加载战役数据

- **WHEN** 后端返回包含 GeoJSON 的战役数据
- **THEN** 地图居中显示到第一个地名坐标，自动调整缩放级别使所有标记点可见

#### Scenario: 点击地名查看详情

- **WHEN** 用户点击地图上的地名标记
- **THEN** 弹出气泡显示地名、来源（CHGIS 精确 / LLM 推断）、古今地名对照（如有）

#### Scenario: 古今地名标签可见

- **WHEN** 地图渲染了 CHGIS 精确匹配的地名
- **THEN** 每个标记下方直接显示两行标签，无需点击即可对照古今地名