# frontend-unit-tests

**Purpose**: 对前端纯函数提供 pytest 单元测试覆盖，在不引入 Node.js 工具链的前提下保证 JS 工具函数正确性。

## Requirements

### Requirement: 纯函数单元测试

项目 MUST 对 `static/js/utils.js` 中无 DOM 依赖的纯函数提供 pytest 单元测试。

测试 SHALL 覆盖以下函数：
- `escHtml(s)`: HTML 转义函数
- `_darkenColor(hex, factor)`: 颜色加深计算
- `_factionColor(faction)`: 阵营颜色映射
- `_computeDataDiagonal(features)`: 数据点集对角线距离计算
- `_terrainColorForType(placeType)`: 地形类型颜色映射

测试文件放置于 `tests/test_frontend_utils.py`。

#### Scenario: escHtml 转义 HTML 特殊字符

- **WHEN** 输入 `"<script>alert('xss')</script>"`
- **THEN** 输出 `<`、`>`、`'` 等特殊字符被转义为 HTML 实体

#### Scenario: _darkenColor 颜色加深

- **WHEN** 输入 `"#ff0000"` 和 factor `0.5`
- **THEN** 输出 `"#7f0000"`（R 通道减半，G/B 保持 0）

#### Scenario: _factionColor 阵营识别

- **WHEN** 输入 `"宋军主力"`
- **THEN** 返回 `"#2b4c7e"`（宋色）
- **WHEN** 输入 `"金兵前锋"`
- **THEN** 返回 `"#c23b22"`（金色）

#### Scenario: _computeDataDiagonal 距离计算

- **WHEN** 传入 2 个点的 features 数组
- **THEN** 返回两点间的地理距离（米），误差 < 1%

#### Scenario: _terrainColorForType 地形颜色

- **WHEN** 输入 `"mountain"`
- **THEN** 返回山脉对应颜色
- **WHEN** 输入 `"unknown_type"`
- **THEN** 返回 `null`