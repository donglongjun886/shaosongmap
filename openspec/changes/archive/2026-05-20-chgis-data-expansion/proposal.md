## Why

当前 CHGIS 测试数据仅 27 条宋代地名，geocoder 命中率极低（实测约 20%），大量地名走 LLM 推断兜底，坐标精度不可靠（偏差可达数百公里），且每次推断消耗 API 额度。需要将数据集扩展到 500+ 条宋代核心地名，使 CHGIS 直接命中成为主流而非例外。

## What Changes

- **下载 CHGIS v6 完整数据集**并筛选宋代时间范围（960-1279）内的府/州/县级别行政地名
- **新增数据预处理脚本**（`scripts/build_chgis.py`）：从 CHGIS v6 原始文件筛选、清洗、输出精简 CSV
- **扩展 `modern_name` 覆盖率**：利用 CHGIS 数据中的现代地名映射，提升古今对照展示
- **提升 fuzzy match 命中率**：更多候选地名 → 更高匹配概率
- **降低 LLM 推断依赖**：预估命中率从 20% → 80%+，减少 API 调用和延迟

## Capabilities

### New Capabilities
- `chgis-data-pipeline`: CHGIS v6 数据下载、筛选（朝代+行政层级）、预处理脚本，输出可供 geocoder 直接加载的 CSV

### Modified Capabilities
- `ancient-place-geocoding`: 地名匹配覆盖率从 ~20% 提升至 80%+；LLM 推断兜底仅用于虚构地名或生僻地点

## Impact

- `data/chgis_v6/chgis_v6_points.csv`: 从 27 条 → 500+ 条（完整替换）
- `scripts/build_chgis.py`: **新增** 数据预处理脚本
- `shaosongmap/geocoder.py`: 不变（CSV 格式兼容，仅数据量增加）
- `requirements.txt`: 可能新增 `requests` 用于下载 CHGIS 数据
