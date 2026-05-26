## MODIFIED Requirements

### Requirement: 扩展后的数据格式兼容

系统 SHALL 确保 `_load_chgis_data()` 函数使用 `@functools.lru_cache(maxsize=1)` 缓存加载结果，同一进程生命周期内仅解析 CSV 一次，后续调用直接返回缓存。

CSV 加载性能 MUST 满足：
- 首次调用正常解析 CSV 文件
- 后续调用返回缓存结果，速度显著快于首次（毫秒级 vs 秒级）
- 缓存不影响数据内容——首次和后续调用返回相同数据

#### Scenario: 首次调用解析 CSV

- **WHEN** 进程启动后首次调用 `_load_chgis_data()`
- **THEN** 正常解析 `chgis_v6_points.csv` 并返回完整地名列表

#### Scenario: 二次调用命中缓存

- **WHEN** 同一进程内第二次调用 `_load_chgis_data()`
- **THEN** 返回缓存数据，不重新打开 CSV 文件，响应时间在毫秒级

#### Scenario: 缓存不影响数据正确性

- **WHEN** 用缓存返回的数据运行 `match_chgis("汴京")`
- **THEN** 返回与无缓存时完全相同的匹配结果（source="chgis"，坐标一致）

#### Scenario: 数据无缝替换

- **WHEN** 用新生成的 `chgis_v6_points.csv` 替换旧文件后运行测试套件
- **THEN** 所有现有测试通过，geocoder 正确加载并匹配新数据中的地名
