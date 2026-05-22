## 1. 数据模型层

- [x] 1.1 新增 `UnitStatus` 枚举（deploying / marching / engaging / retreating / routing）
- [x] 1.2 新增 `TroopType` 枚举（infantry / cavalry / mixed）
- [x] 1.3 新增 `ForceUnit` Pydantic 模型（name, faction, commander, troop_type, troop_count, direction）
- [x] 1.4 新增 `UnitState` Pydantic 模型（seq, unit_name, status, location, direction, description）
- [x] 1.5 `CampaignTimeline` 新增 `units: list[ForceUnit]` 和 `unit_states: list[UnitState]` 字段

## 2. LLM 提取层

- [x] 2.1 扩展 `_TIMELINE_SYSTEM_PROMPT`，新增部队实体提取规则（含进攻方向字段 `direction`）和 JSON schema
- [x] 2.2 新增 `_validate_unit_states()` 后处理函数，校验 unit_state 的 seq 和 unit_name 有效性
- [x] 2.3 新增 `_deduplicate_unit_names()` 后处理函数，用编辑距离合并名称变体
- [x] 2.4 更新 `extract_timeline()` 函数，解析 units 和 unit_states 字段

## 3. API 层

- [x] 3.1 `/api/extract` SSE result 事件新增 `units` 和 `unit_states` 字段
- [x] 3.2 实现块状箭头 GeoJSON Polygon 生成函数：根据位置+方向+状态+scale 计算箭头体的四个角点坐标
- [x] 3.3 实现同地多部队箭头平行错位计算（沿进攻方向并排偏移，间距=箭头宽度×1.2）
- [x] 3.4 实现 scale 自适应简化：strategic 级别返回细线 LineString，battle/tactical 级别返回 Polygon

## 4. 前端——块状箭头地图图层

- [x] 4.1 新增部队箭头 GeoJSON source 和 fill 图层（阵营色填充+状态边框）
- [x] 4.2 实现箭头形态驱动函数：根据 status 生成对应的 GeoJSON 几何（矩形/箭头/散点）
- [x] 4.3 实现部队箭头 step 过滤（复用现有 `['<=', ['get', 'step'], currentStep]` 模式）
- [x] 4.4 实现溃散碎裂动画（箭头 Polygon → 散点 MultiPoint，opacity 递减三个步骤至消失）
- [x] 4.5 实现箭头生长动画（首次出现时从箭尾到箭尖逐步展开，600ms）
- [x] 4.6 实现箭头转向动画（direction 变化时箭尖旋转过渡，400ms）
- [x] 4.7 实现状态切换渐变（边框颜色/宽度/虚线样式在 600ms 内过渡）
- [x] 4.8 实现 scale 自适应渲染（监听 zoom 变化，切换细线/标准箭头/详细箭头）

## 5. 前端——部队 UI 组件

- [x] 5.1 在事件卡片下方新增部队状态卡片（状态图标+部队名+状态标签+描述）
- [x] 5.2 在图例区新增「部队」分组（各阵营箭头样式预览+图层可见性 checkbox）
- [x] 5.3 实现部队箭头点击 popup（部队名、阵营、指挥官、兵力、状态、进攻方向、描述）

## 6. 测试

- [x] 6.1 编写 `ForceUnit` 和 `UnitState` 模型的单元测试
- [x] 6.2 编写 `_validate_unit_states()` 和 `_deduplicate_unit_names()` 的单元测试
- [x] 6.3 编写块状箭头 GeoJSON 生成函数的单元测试（验证 Polygon 顶点坐标正确性）
- [x] 6.4 编写 `/api/extract` timeline 模式下返回 units/unit_states 的集成测试
- [x] 6.5 用探讨论中的绍宋战役段落做端到端验证
