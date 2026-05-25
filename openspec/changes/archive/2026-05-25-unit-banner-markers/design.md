## Context

当前部队可视化使用 NATO APP-6A 块状箭头（Polygon 填充），与项目追求的汉代《驻军图》古地图风格矛盾。路线（朱砂虚线+箭镞）和地名（城池▭/营寨▲图标）已统一为古地图风格，部队标记是最后一个不协调元素。

参考西汉《驻军图》实物，汉代用双线矩形套框标注部队驻地，红色三角标指挥部，红色虚线标行军路线。

## Goals / Non-Goals

**Goals:**
- 部队标记从 Polygon 箭头改为"旗帜图标 + 方向指示线"组合
- 与城池图标保持一致的"双线套框"视觉语言
- 保留多单位同地偏移逻辑，避免重叠
- 保留时间轴步骤过滤和图层切换功能

**Non-Goals:**
- 不改变 GeoJSON FeatureCollection 的 API 结构
- 不引入新的外部依赖
- 不改变部队弹窗交互逻辑
- 不添加交叉剑/火铳等复杂战斗符号

## Decisions

### 1. 旗帜图标：Canvas offscreen 绘制双线套框

**选择：** Canvas 2D 绘制双线矩形（外框墨线 + 内框阵营色 + 半透明填充 + 顶部三角旗标），通过 `map.addImage()` 注册为 MapLibre symbol 图标。

**替代方案：** SVG icon-image 或纯 HTML Marker。Canvas 更轻量，与现有城池/营寨图标统一。

### 2. 特征分类：`_feature_type` 属性

**选择：** 在 GeoJSON properties 中使用 `_feature_type` 字段（`unit_banner` / `unit_direction`）区分特征类型，替代原来的 `geometry.type === 'Polygon'` 判断。

**原因：** Point 类型既用于地名也用于旗帜位置，LineString 既用于路线也用于方向线。单一几何类型判断不可靠。

### 3. 方向线：短虚线 + 末端箭镞

**选择：** 从旗帜锚点沿方向角偏移 `direction_len_m` 距离，生成 LineString，配 `line-dasharray: [6, 3]` 虚线样式，复用现有 `arrowhead` 图标作为末端指示。

**原因：** 与路线（朱砂虚线+箭镞）保持一致的视觉语言。

### 4. 交战状态：旗帜变红，不叠加交叉剑

**选择：** `engaging` 状态直接切换为朱砂红色图标 `banner-engaging`，不额外叠加图标。

**原因：** 保持简洁，避免图标堆叠造成的视觉噪音。汉代地图本身也不使用交叉符号。

### 5. 无方向时仅显示旗帜

**选择：** `_make_unit_banner_features` 在方向为 None 时只返回 Point 特征，不生成 LineString。

## Risks / Trade-offs

- **旗帜重叠风险：** 多单位同坐标时旗帜图标可能重叠 → 保留现有 `_compute_unit_offsets` 坐标偏移逻辑
- **缩放可读性：** 高 zoom 下旗帜可能偏小 → 使用 zoom step 表达式自适应图标大小
