# Campaign Map Rendering 战役地图渲染

## Purpose

交互式地图渲染——文本输入/OCR识别 → 地图标记与路线展示，支持输入/查看模式切换、引导态/结果态自适应、时间轴增量渲染、古今地名对照标签、图例过滤、键盘快捷键。
## Requirements
### Requirement: 战役文本输入与提交

系统 SHALL 提供一个 Web 页面，包含**文本输入区域和截图上传区域**，供读者通过粘贴战役文本**或上传截图**两种方式请求生成地图。

#### Scenario: 用户粘贴文本并提交

- **WHEN** 用户在 textarea 中粘贴战役文本并点击「生成地图」按钮
- **THEN** 系统发送 POST 请求到 `/api/extract`，并在收到响应后在地图上渲染结果

#### Scenario: 用户上传截图并提交

- **WHEN** 用户通过拖拽或粘贴上传一张包含战役文本的截图
- **THEN** 系统调用 `/api/ocr` 进行文字识别，将清洗后的文本自动填入 textarea，用户可校对后点击「生成地图」

#### Scenario: 空文本提交

- **WHEN** 用户提交空的或仅含空白的文本（textarea 为空且未上传截图）
- **THEN** 前端阻止提交并提示「请输入战役文本或上传截图」

#### Scenario: OCR 识别失败

- **WHEN** 用户上传的截图经 OCR 识别后清洗所得文本不足 50 字符
- **THEN** 前端显示错误提示「未能从截图中提取到足够的文本，请确保截图包含正文内容」

### Requirement: 交互式地图渲染

系统 SHALL 使用 MapLibre GL JS 在浏览器中渲染交互式地图，底图由 Basemap Provider 架构根据 scale 自动选择（tactical→纯色 schematic，battle/strategic→低饱和 OSM muted_osm）。地图 MUST 根据当前页面模式采用不同的初始状态，在 timeline 模式下支持按事件步骤增量渲染。

地图 MUST 支持：
- 鼠标缩放（+/-）和拖拽平移
- 按 `source` 字段区分地名标记样式（实心=CHGIS，空心=LLM 推断）
- **地名标记使用 zoom 表达式动态调整 circle-radius 和 text-size**，远视角缩小、近视角放大
- **CHGIS 精确匹配的地名标记通过两个独立文字标签层分别显示古地名和今地名**：古地名层（`place-labels-ancient`）显示深色粗体标签，今地名对照层（`place-labels-modern`）显示灰色斜体标签，LLM 推断地名仅在古地名层显示单行标签
- **古地名标签层和今地名标签层可在地图图例区通过 checkbox 独立切换可见性**
- 行军路线以带箭头线条展示
- 每条路线可独立显示/隐藏
- 在 timeline 模式下，路线根据当前事件步数动态显示/隐藏：seq ≤ currentStep 的事件涉及的路线段可见，其余隐藏
- 在 timeline 模式下，地名标记根据事件触发状态切换样式：当推进到触发某地名的事件时，该标记从灰色变为高亮色
- **部队以块状箭头（宽箭身+方向箭尖）展示在地图上，箭身宽度表达进攻正面/兵力规模，箭尖指向进攻方向，统一表达位置-方向-规模三个维度**
- **部队箭头通过形态区分状态：待命（无箭尖矩形）、进军（完整箭头）、交战（箭头+红色粗边框）、撤退（细虚线反向箭）、溃散（碎裂散点）**
- **部队箭头在 timeline 模式下根据当前 step 动态更新：仅 seq ≤ currentStep 且 status ≠ routing 的部队显示完整箭头；溃散部队在触发步骤后碎裂为散点并逐步淡出（三个步骤后完全消失）**
- **多个部队关联同一地名时，箭头沿进攻方向平行错位避免重叠**
- **箭头尺寸根据数据范围自适应**：尺寸 = 数据包围盒对角线 × scale 系数（tactical 20% / battle 8% / strategic 3%），确保不同范围下屏幕占比一致
- **箭头形状优化为宽长比 1:3.5，头部占全长 40%**，视觉上更修长、方向感更强
- **箭头根据 map scale 自适应：strategic 级别简化为细线箭头，tactical 级别展示完整宽箭身+详细标签**
- **部队箭头图层可在地图图例区通过 checkbox 独立切换可见性**

地图在三种页面状态下 MUST 采用不同的初始化和交互行为：

| 状态 | 触发条件 | 地图行为 |
|------|---------|---------|
| 引导态 | 页面初次加载 / 返回输入模式且无数据 | center [112,33] zoom 5，可自由浏览 |
| 结果态 | 提交成功进入查看模式 | fitBounds 聚焦数据范围，scale 控制 maxZoom |
| 编辑态 | 查看模式下点击重新渲染 | 同结果态，但不改变当前模式 |

#### Scenario: 地图加载战役数据

- **WHEN** 后端返回包含 GeoJSON 的战役数据
- **THEN** 地图居中显示到第一个地名坐标，自动调整缩放级别使所有标记点可见

#### Scenario: 输入模式下地图为引导态

- **WHEN** 页面处于输入模式（首次加载或从查看模式返回）
- **THEN** 地图不做 fitBounds，保持中国全景视图，用户可自由浏览地图

#### Scenario: 查看模式下地图聚焦战役

- **WHEN** 提交成功后切换到查看模式
- **THEN** 地图根据 scale 字段调整 maxZoom（tactical=14 / battle=10 / strategic=6），并 fitBounds 到所有地名和路线坐标

#### Scenario: 点击地名查看详情

- **WHEN** 用户点击地图上的地名标记
- **THEN** 弹出气泡显示地名、来源（CHGIS 精确 / LLM 推断）、古今地名对照（如有）

#### Scenario: 古今地名标签可见

- **WHEN** 地图渲染了 CHGIS 精确匹配的地名
- **THEN** 每个标记下方通过两个独立符号层显示两行标签，无需点击即可对照古今地名；用户可在地图图例区独立切换任一标签层的可见性

#### Scenario: Timeline 模式下路线动态生长

- **WHEN** 用户在 timeline 模式下从步骤 2 推进到步骤 3，且步骤 3 包含新行军路线段
- **THEN** 新路线段在地图上出现，已有路线保持显示

#### Scenario: Timeline 模式下路线回缩

- **WHEN** 用户在 timeline 模式下从步骤 5 回退到步骤 4
- **THEN** 仅步骤 5 独有的路线段隐藏，步骤 1-4 的路线保持显示

#### Scenario: Timeline 模式下地名按事件高亮

- **WHEN** 用户推进到步骤 3，该步骤事件涉及地名「蔡州」
- **THEN**「蔡州」标记从灰色低亮状态切换为高亮色，其他未触发地名保持灰色半透明

#### Scenario: Timeline 模式下部队箭头随步骤更新

- **WHEN** 用户推进到步骤 4，合扎猛安首次出现
- **THEN** 合扎猛安块状箭头通过生长动画（箭尾→箭尖逐步绘制）和 opacity 渐变（600ms）出现在关联地名位置

#### Scenario: Timeline 模式下溃散部队碎裂消失

- **WHEN** 用户推进到步骤 5，焦文通部状态变为 routing；继续推进到步骤 6、7
- **THEN** 焦文通部箭头碎裂为灰色散点，opacity 在步骤 5→7 间从 0.6 递减到 0，步骤 8 时完全隐藏

#### Scenario: 点击部队箭头查看详情

- **WHEN** 用户点击地图上的部队块状箭头
- **THEN** 弹出气泡显示部队名称、阵营、指挥官、兵力、当前状态、进攻方向和简要描述

#### Scenario: 部队图例可见性切换

- **WHEN** 用户在图层图例中取消勾选「部队」checkbox
- **THEN** 地图上所有部队块状箭头隐藏，地名和路线不受影响

#### Scenario: 地图不依赖外部瓦片服务

- **WHEN** 页面加载地图
- **THEN** 地图渲染纯色背景（`#f5f0e1`），不发起任何外部瓦片网络请求

#### Scenario: 战术级近视角标记放大

- **WHEN** 地图 zoom ≥ 12（战术级近视角）
- **THEN** 地名 circle-radius 为 14px，text-size 为 15px，便于识别单个战场细节

#### Scenario: 底图根据 scale 自动选择

- **WHEN** 提取结果 scale 为 battle 或 strategic
- **THEN** 地图自动使用 `muted_osm` 低饱和 OSM 底图，提供地形参照

### Requirement: 提取结果面板

系统 SHALL 在地图旁展示提取结果的结构化信息面板，包含战役名称、双方信息、地名列表、行军路线。**面板中的地名、将领、路线字段 MUST 可编辑，用户修改后可通过「重新渲染」按钮更新地图。**

#### Scenario: 查看提取结果

- **WHEN** 后端返回战役数据
- **THEN** 结果面板显示战役名、双方将领和兵力、地名列表（含坐标）、行军路线描述

#### Scenario: 编辑地名并重新渲染

- **WHEN** 用户修改地名文本，然后点击「重新渲染」
- **THEN** 系统调用 `/api/render`，使用修正后的地名重新匹配坐标，地图标记更新

#### Scenario: 删除错误将领

- **WHEN** 用户点击将领旁的删除按钮
- **THEN** 该将领从阵营中移除，结果面板更新

#### Scenario: 添加遗漏地名

- **WHEN** 用户点击「+ 添加地名」并输入地名
- **THEN** 新地名加入列表，点击「重新渲染」后系统为其匹配坐标并在图上标记

### Requirement: 加载和错误状态处理

系统 SHALL 在请求期间通过**分阶段进度条**显示管道进展，并在请求失败时显示可理解的错误信息。

进度条 MUST 包含以下阶段节点：
- 识别文字（仅截图流程）
- 提取结构数据
- 匹配古地名
- 渲染地图

每个阶段完成时对应节点亮起绿色 ✓。失败阶段显示红色 ✗ 并附带错误描述。

#### Scenario: 分阶段进度展示

- **WHEN** 文本提交后管道开始执行
- **THEN** 进度条依次点亮各阶段节点（✓ 提取结构 → ⏳ 匹配古地名 → ○ 渲染地图）

#### Scenario: 某阶段失败时的进度展示

- **WHEN** 管道在 geocode 阶段失败
- **THEN** 进度条显示 ✓提取结构 → ✗匹配古地名（附错误原因），停止后续阶段

#### Scenario: 后端返回错误

- **WHEN** 后端返回 4xx 或 5xx 错误
- **THEN** 前端显示错误提示（如「提取失败，请检查文本格式」或「服务暂不可用，请稍后重试」）

### Requirement: 键盘快捷键

系统 SHALL 支持以下键盘快捷键提升操作效率。

#### Scenario: Ctrl+Enter 提交文本

- **WHEN** 用户在 textarea 中按下 Ctrl+Enter（macOS 为 Cmd+Enter）
- **THEN** 系统触发与点击「生成地图」按钮相同的提交流程

#### Scenario: Esc 关闭弹窗

- **WHEN** 用户按下 Esc 键
- **THEN** 地图上所有打开的 popup 关闭，错误提示可被关闭

### Requirement: Comic 主题地形色块图层

系统 SHALL 在 comic 主题（tactical 级）下渲染地形色块图层，以半透明色块标示山川河谷的示意位置。

地形色块 MUST：
- 渲染在底图之上、标记和路线之下（z-index 层级：底图 < 色块 < 路线 < 标记 < 标签）
- 通过 MapLibre `fill` layer 实现，source 为动态生成的 GeoJSON
- 每个色块半径为数据包围盒对角线的 5%（最小 500m，最大 5000m）
- 色块不可交互（无 click/hover 事件）

#### Scenario: 山脉和河流色块渲染

- **WHEN** comic 主题激活且战役数据包含 `place_type: mountain` 和 `place_type: river`
- **THEN** 地图上以地名坐标为中心渲染对应颜色的半透明圆形色块

#### Scenario: 地形色块在路线下方

- **WHEN** comic 主题激活且某地形色块与行军路线空间重叠
- **THEN** 路线线条始终渲染在色块上方，不被色块遮挡

### Requirement: Comic 主题箭头加粗与笔触感

系统 SHALL 在 comic 主题下将行军路线和方向箭头渲染为更粗壮的毛笔笔触风格。

箭头 MUST：
- 线宽为基础线宽的 1.5 倍（tactical 级约 3.5px）
- 颜色使用阵营色（由 CSS 变量驱动）
- 起笔端添加小圆点（直径 = 线宽 × 1.8）模拟毛笔顿笔
- 末端箭头尺寸放大 20%
- 通过 MapLibre line layer 的 `line-cap: round` 和 `line-width` 实现

#### Scenario: Comic 主题下金军箭头加粗变红

- **WHEN** comic 主题激活且行军路线涉及金军
- **THEN** 箭头线宽 3.5px，朱砂红色，起笔端有圆形顿笔点

### Requirement: Comic 主题印章叠加层

系统 SHALL 在 comic 主题下于地图容器右下角叠加一个不可交互的红色印章 SVG 元素。

印章 MUST：
- 位于地图容器右下角，距边缘 24px
- 用 `position: absolute` 的 div + 内联 SVG 实现
- 颜色 `#c23b22`，opacity 0.85
- 约 15 度旋转（CSS `transform: rotate(-15deg)`）
- 文字为战役名前 4 字（不足则全部显示），无战役名时不渲染
- `pointer-events: none`，不影响地图交互

#### Scenario: 印章显示

- **WHEN** comic 主题激活且 campaign_name 为「东坡塬遭遇战」
- **THEN** 印章显示「东坡塬遭」，右下角 24px 处

#### Scenario: 无战役名隐藏印章

- **WHEN** comic 主题激活但 campaign_name 为 null
- **THEN** 印章 div 存在但内容为空，不占视觉空间

### Requirement: Comic 主题地名标签光晕

系统 SHALL 在 comic 主题下通过 MapLibre text-halo 属性为地名标签添加半透明白色光晕，防止地形色块干扰文字可读性。

光晕 MUST：
- `text-halo-color`: `rgba(255,255,255,0.75)`
- `text-halo-width`: 2.5px（比默认值大 1px）
- `text-halo-blur`: 0.5px
- 仅 comic 主题下生效

#### Scenario: 标签在地形色块上可读

- **WHEN** comic 主题激活且标签「东坡塬」位于浅棕绿色块上方
- **THEN** 标签文字周围显示白色光晕，文字与色块边界清晰

### Requirement: 行军路线虚线样式优化

系统 SHALL 调整行军路线的虚线参数以减少视觉断裂感，同时保持古地图风格。

路线 `line-dasharray` MUST：
- 默认模式（battle/strategic）：`[6, 3]`（原 `[8, 4]`，实线段从 8px 缩至 6px，间隙从 4px 缩至 3px）
- Comic 主题（tactical）：`[6, 3]`（原 `[10, 5]`）

此变更 MUST 不改变路线的颜色、线宽、opacity 等其他 paint 属性。

#### Scenario: 默认模式下路线虚线更紧凑

- **WHEN** 地图在 battle 或 strategic 级别渲染行军路线
- **THEN** 路线虚线使用 `[6, 3]` 参数，视觉上比 `[8, 4]` 更连续

#### Scenario: Comic 主题下路线虚线同步调整

- **WHEN** comic 主题激活（tactical 级）渲染行军路线
- **THEN** 路线虚线同样使用 `[6, 3]`，与 comic 主题的加粗线宽（3.5px）配合

### Requirement: 行军路线端点锚点标记

系统 SHALL 在每条行军路线的起止点渲染小型圆形锚点标记，使路线与地名/部队标记之间的空间连接关系更清晰。

锚点 MUST：
- 渲染在路线首末坐标处，通过独立的 `route-anchors` GeoJSON source 和 circle layer 实现
- 颜色为朱砂红 `#c23b22`，opacity 0.5
- 半径 3px（circle-radius），无描边
- 不可交互（无 click/hover 事件）
- 图层位于 `route-lines` 之上、地名标记之下
- 仅在 route features 数量 > 0 时渲染

锚点数据 MUST 在前端从路线的 LineString 坐标中提取：首坐标为首点、末坐标为末点。若路线仅含一个坐标（退化为点），则不生成锚点。

#### Scenario: 单条路线的首末锚点

- **WHEN** 地图渲染一条从「黄龙岭」到「岭北」的路线
- **THEN**「黄龙岭」和「岭北」坐标处各显示一个 3px 朱砂色小圆点，标识路线起止

#### Scenario: 多条路线各有独立锚点

- **WHEN** 地图渲染三条行军路线
- **THEN** 每条路线的首末点各有一个锚点，总计六个锚点

#### Scenario: 无路线时不渲染锚点层

- **WHEN** 战役数据无行军路线
- **THEN** `route-anchors` 的 GeoJSON source 包含空 FeatureCollection，circle layer 不渲染任何内容

#### Scenario: Comic 主题下锚点同样渲染

- **WHEN** comic 主题激活，地图上存在行军路线
- **THEN** 锚点 circle layer 正常渲染，样式与默认模式一致

