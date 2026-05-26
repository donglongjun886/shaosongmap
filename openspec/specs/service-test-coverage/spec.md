# Service Test Coverage 服务层测试覆盖率

## Purpose

确保服务层（services/）所有模块的单元测试覆盖率达到 80% 以上，保障核心业务逻辑的正确性。

## Requirements

### Requirement: unit_banner 模块测试覆盖率 ≥80%

`services/unit_banner.py` 模块的测试覆盖率 SHALL 达到 80% 以上。

测试 MUST 覆盖以下逻辑：
- `make_unit_banner_features()` 生成旗帜标记 GeoJSON 特征
- `compute_unit_offsets()` 同地多部队错位偏移计算
- `make_unit_geojson()` 完整部队 GeoJSON 生成流程
- 边界条件：空输入、无效坐标、缺失字段

#### Scenario: 正常部队标记生成

- **WHEN** 传入包含部队名、坐标、编制类型的有效输入
- **THEN** `make_unit_banner_features()` 返回包含 Point 特征的 GeoJSON 列表

#### Scenario: 空输入处理

- **WHEN** 传入空的部队列表
- **THEN** `make_unit_geojson()` 返回空列表，不抛异常

### Requirement: geo 模块测试覆盖率 ≥80%

`services/geo.py` 模块的测试覆盖率 SHALL 达到 80% 以上。

测试 MUST 覆盖：
- 方位词→角度转换（angle_for_direction）
- 包围盒对角线计算（compute_data_diagonal）
- 坐标偏移（offset_point）

#### Scenario: 角度转换

- **WHEN** 传入方位词如「东」「北」「西南」
- **THEN** 返回对应角度值（正东=0°，逆时针）

#### Scenario: 坐标偏移

- **WHEN** 传入有效经纬度和偏移参数
- **THEN** 返回正确的偏移后坐标

### Requirement: geojson 模块测试覆盖率 ≥80%

`services/geojson.py` 模块的测试覆盖率 SHALL 达到 80% 以上。

测试 MUST 覆盖：
- GeoJSON Feature 对象生成
- FeatureCollection 组装
- 属性附加（地名、类型、坐标）
- 边界条件：空几何、空属性

#### Scenario: Feature 生成

- **WHEN** 传入地名、坐标和类型
- **THEN** 返回符合 RFC 7946 规范的 GeoJSON Feature 对象

#### Scenario: 空属性处理

- **WHEN** 传入空的属性字典
- **THEN** 生成的 Feature 仍为合法 GeoJSON，properties 为空对象 `{}`