# Service Test Coverage 服务层测试覆盖率

## ADDED Requirements

### Requirement: unit_banner 模块测试覆盖率 ≥80%

`services/unit_banner.py` 模块的测试覆盖率 SHALL 达到 80% 以上。

测试 MUST 覆盖以下逻辑：
- `create_banner_html()` 生成可渲染的 HTML 片段
- `add_unit_markers()` 正确调用 folium 添加标记
- 军队编制名（如"左军"、"中军"、"右军"）的文本解析
- 边界条件：空输入、无效坐标、缺失字段

所有测试 SHALL 使用 mock 隔离 folium 和 streamlit 依赖。

#### Scenario: 正常部队标记生成

- **WHEN** 传入包含部队名、坐标、编制类型的有效输入
- **THEN** `add_unit_markers()` 成功在 mock folium 地图上添加对应标记

#### Scenario: 空输入处理

- **WHEN** 传入空的部队列表
- **THEN** `add_unit_markers()` 不添加任何标记，不抛异常

### Requirement: geo 模块测试覆盖率 ≥80%

`services/geo.py` 模块的测试覆盖率 SHALL 达到 80% 以上。

测试 MUST 覆盖：
- 两点距离计算（Haversine 公式）
- 多点中点/中心点计算
- 坐标格式校验与转换

#### Scenario: 距离计算

- **WHEN** 传入两个有效经纬度坐标
- **THEN** 返回正确的球面距离（精度 ±0.01 km）

#### Scenario: 无效坐标处理

- **WHEN** 传入超出范围的纬度值（如 >90 或 <-90）
- **THEN** 函数返回错误标识或抛出明确异常

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