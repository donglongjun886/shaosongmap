## Requirements

### Requirement: CHGIS v6 数据下载与预处理

系统 SHALL 提供数据预处理脚本 `scripts/build_chgis.py`，从 CHGIS v6 官方数据源下载原始数据，筛选宋代（960-1279）府/州/军/监/县级行政地名，输出与 geocoder 兼容的精简 CSV。

筛选规则 MUST：
- 时间范围筛选：`beg_yr <= 1279 AND end_yr >= 960`（地名存在期与宋朝有交集）
- 行政层级筛选：仅保留 `府`、`州`、`军`、`监`、`县` 级别
- 坐标完整性：`x_coord` 和 `y_coord` 均不为空

输出 CSV MUST 包含列：`name_ch, x_coord, y_coord, beg_yr, end_yr, lev, modern_name`

#### Scenario: 成功下载并筛选数据

- **WHEN** 运行 `python scripts/build_chgis.py`
- **THEN** 脚本从 Harvard Dataverse 下载 CHGIS v6 原始数据，筛选后输出 `data/chgis_v6/chgis_v6_points.csv`，包含至少 500 条地名记录

#### Scenario: 下载失败处理

- **WHEN** CHGIS 数据源不可达或网络不通
- **THEN** 脚本打印错误信息并退出（返回码 1），不覆盖已有 CSV 文件

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

### Requirement: 数据覆盖率达标

系统 SHALL 在扩展后的 CHGIS 数据集中覆盖《绍宋》等宋代历史小说中常见的府/州级地名至少 80%。

常见地名示例（SHALL 能在数据中匹配到）：
- 五京：汴京（东京）、临安（行在）、西京（洛阳）、南京（商丘）、北京（大名）
- 边疆州府：兴庆府、灵州、夏州、银州、绥州、宥州
- 关键战场：黄龙府、幽州

#### Scenario: 常见宋代地名命中测试

- **WHEN** 运行 `match_chgis("汴京")` 使用扩展后的数据
- **THEN** 返回 CHGIS 精确匹配（经度约 114.35，纬度约 34.80），置信度 ≥ 0.9

#### Scenario: 边疆地名命中

- **WHEN** 运行 `match_chgis("兴庆府")` 使用扩展后的数据
- **THEN** 返回 CHGIS 精确匹配，source 为 "chgis"