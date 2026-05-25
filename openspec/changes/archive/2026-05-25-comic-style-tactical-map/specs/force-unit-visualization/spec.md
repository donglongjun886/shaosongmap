# Force Unit Visualization 部队可视化 (Delta)

## ADDED Requirements

### Requirement: Comic 主题部队标记样式

系统 SHALL 在 comic 主题（tactical 级）下使用阵营色填充矩形框+白色文字渲染部队标记，替换现有的双线套框旗帜样式。Battle/strategic 级 MUST 保持现有双线套框样式不变。

Comic 主题部队标记 MUST：
- 使用阵营色填充矩形框（无三角旗标），白色文字标注部队名称
- 宋军标记：靛蓝 `#2b4c7e` 填充 + 白色文字
- 金军标记：朱砂红 `#c23b22` 填充 + 白色文字
- 未知阵营标记：墨色 `#2c2c2c` 填充 + 白色文字
- 标记尺寸：文字长度自适应，固定高度约 24px，内边距 6px 12px
- 边框：比填充色深 15% 的同色系边框，1.5px 宽
- 方向指示线保持实线样式（非虚线），使用同阵营色，线宽 2.5px
- 标记通过 MapLibre `image` 类型的 symbol layer 渲染（Canvas 离线生成 icon）

标记样式切换 MUST：
- 根据 scale 自动判断：tactical → comic 样式，battle/strategic → 双线套框样式
- 图例 checkbox 中「部队旗帜」在 comic 主题下文案改为「部队标记」

#### Scenario: Comic 主题下宋军标记样式

- **WHEN** comic 主题激活且部队「焦文通部」阵营为宋军
- **THEN** 地图上渲染靛蓝底白字矩形框标记，文字为「焦文通部」，无三角旗标

#### Scenario: Comic 主题下金军标记样式

- **WHEN** comic 主题激活且部队「合扎猛安」阵营为金军
- **THEN** 地图上渲染朱砂红底白字矩形框标记，文字为「合扎猛安」

#### Scenario: Comic 主题下方向线为实线

- **WHEN** comic 主题激活且部队有 direction 字段
- **THEN** 方向指示线为实线（非虚线），线宽 2.5px，颜色与标记框阵营色一致

#### Scenario: Battle 级保持双线套框

- **WHEN** scale 为 `battle`（非 tactical）
- **THEN** 部队标记使用现有双线套框+三角旗标样式，不受 comic 主题影响