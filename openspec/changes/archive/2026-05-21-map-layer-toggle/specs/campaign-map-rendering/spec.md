## MODIFIED Requirements

### Requirement: 交互式地图渲染

系统 SHALL 使用 MapLibre GL JS 在浏览器中渲染交互式地图，底图使用 OpenStreetMap 瓦片。

地图 MUST 支持：
- 鼠标缩放（+/-）和拖拽平移
- 按 `source` 字段区分地名标记样式（实心=CHGIS，空心=LLM 推断）
- **CHGIS 精确匹配的地名标记通过两个独立文字标签层分别显示古地名和今地名**：古地名层（`place-labels-ancient`）显示深色粗体标签，今地名对照层（`place-labels-modern`）显示灰色斜体标签，LLM 推断地名仅在古地名层显示单行标签
- 行军路线以带箭头线条展示
- 每条路线可独立显示/隐藏
- **古地名标签层和今地名标签层可在地图图例区通过 checkbox 独立切换可见性**

#### Scenario: 地图加载战役数据

- **WHEN** 后端返回包含 GeoJSON 的战役数据
- **THEN** 地图居中显示到第一个地名坐标，自动调整缩放级别使所有标记点可见

#### Scenario: 点击地名查看详情

- **WHEN** 用户点击地图上的地名标记
- **THEN** 弹出气泡显示地名、来源（CHGIS 精确 / LLM 推断）、古今地名对照（如有）

#### Scenario: 古今地名标签可见

- **WHEN** 地图渲染了 CHGIS 精确匹配的地名
- **THEN** 每个标记下方通过两个独立符号层显示两行标签，无需点击即可对照古今地名；用户可在地图图例区独立切换任一标签层的可见性
