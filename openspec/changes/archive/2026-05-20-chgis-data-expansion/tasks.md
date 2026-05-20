## 1. 数据预处理脚本

- [x] 1.1 创建 `scripts/build_chgis.py`：从 Harvard Dataverse 下载 CHGIS v6 原始数据（v6_time_pref_pts_wgs84 或等效文件），解压 zip
- [x] 1.2 实现时间范围筛选：`beg_yr <= 1279 AND end_yr >= 960`（地名存在期与宋朝有交集）
- [x] 1.3 实现行政层级筛选：仅保留 府/州/军/监/县 级别，排除更低层级
- [x] 1.4 实现坐标完整性过滤：`x_coord` 和 `y_coord` 均不为空
- [x] 1.5 输出与 geocoder 兼容的 CSV（`name_ch, x_coord, y_coord, beg_yr, end_yr, lev, modern_name`），写入 `data/chgis_v6/chgis_v6_points.csv`

## 2. 数据生成与替换

- [x] 2.1 运行 `python scripts/build_chgis.py` 生成新 CSV，确认记录数 ≥ 500 条
- [x] 2.2 人工抽查关键地名覆盖率：五京（汴京/临安/西京/南京/北京）、边疆州府（兴庆府/灵州/夏州）、关键战场（黄龙府/幽州/朱仙镇）

## 3. 兼容性验证

- [x] 3.1 运行现有 geocoder 测试套件（`pytest tests/ -k "chgis or geocode" -v`），确保全部通过
- [x] 3.2 运行完整测试套件（`pytest tests/ -v`），确保无回归