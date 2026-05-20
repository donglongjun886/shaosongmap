## Context

当前 `data/chgis_v6/chgis_v6_points.csv` 仅 27 条手工挑选的宋代地名样本，覆盖了极少数的府级地名（汴京、临安等）。实际《绍宋》等小说涉及的地名远不止这些——横山、唐州、邓州、兴庆府、朱仙镇、阴山、黄龙府等大量地名全部走 LLM 推断，导致坐标精度差且消耗 API 额度。

CHGIS v6 完整数据集包含数万条历史地名记录，每条有时间范围（`beg_yr` ~ `end_yr`）和行政层级（`lev`），可直接筛选宋代府/州/县级地名。

## Goals / Non-Goals

**Goals:**
- 将 CHGIS 数据从 27 条扩展到 500+ 条宋代（960-1279）府/州/县级地名
- 提供可复现的数据预处理脚本（`scripts/build_chgis.py`）
- `modern_name` 字段覆盖率提升至 60%+
- 保持现有 geocoder 代码零改动（CSV 列格式兼容）

**Non-Goals:**
- 不做全文 CHGIS 导入（数据量过大，>100MB，不适合 repo）
- 不做实时 CHGIS API 查询（保持离线可用）
- 不改动 geocoder 的匹配算法
- 不引入数据库（保持 CSV 文件加载）

## Decisions

### 1. 数据来源与筛选策略

**选择**: 使用 CHGIS v6 官方数据（Fairbank Center, Harvard），筛选条件：
- `beg_yr <= 1279 AND end_yr >= 960`（与宋朝有交集）
- `lev` 为 `府` / `州` / `军` / `监` / `县`（排除更低层级）
- 合并 `name_ch` 和 `name_py` 两列做模糊匹配

**理由**: CHGIS v6 是学术界标准数据集，坐标精度可靠。宋代时间范围筛选可将数据量从数万缩至数百条。排除村/镇级地名可减少噪音。

**替代方案**:
- Google/百度地图 API → 现代坐标，无法匹配古地名，不是同一问题
- 纯 LLM → 精度差，每次 API 调用有延迟和费用
- 维基百科爬虫 → 数据质量不可控，维护成本高

### 2. 数据文件大小控制

**选择**: 筛选后 CSV 控制在 50KB 以内（约 500-800 条记录），直接放入 `data/chgis_v6/` 目录，跟随 git 管理。

**理由**: 
- 文件小，不影响 clone/push 速度
- 不需要下载步骤，clone 即可用
- 不需要外部数据依赖

### 3. 预处理脚本设计

**选择**: `scripts/build_chgis.py` 从 CHGIS 原始文件（如 `v6_time_pref_pts_wgs84`）筛选并输出精简 CSV。

脚本功能：
1. 读取 CHGIS v6 原始 TSV/CSV 文件
2. 按时间范围和行政层级筛选
3. 按 `lev_zh`（层级中文名）分类：府/州/军/监/县
4. 输出与当前 geocoder 兼容的 CSV 格式（`name_ch, x_coord, y_coord, beg_yr, end_yr, lev, modern_name`）

**理由**: 可复现、可审查、可重新生成

### 4. 向后兼容

**选择**: 输出 CSV 列格式与当前 `chgis_v6_points.csv` 完全一致，geocoder.py 零改动。

**理由**: 减少回归风险，数据替换不涉及代码变更。

## Risks / Trade-offs

- **CHGIS 数据下载依赖外部源**: CHGIS v6 原始数据托管在 Harvard Dataverse (https://dataverse.harvard.edu/dataverse/chgis_v6) → 在 `scripts/build_chgis.py` 中通过 URL 下载 zip 并解压
- **宋代县级地名可能有误**: CHGIS 对县的考证不如府州完整 → 优先确认府/州级数据，县级标记为 `lev=县` 供前端区分
- **模糊匹配阈值不变可能导致漏配**: 增加候选量后，原 0.8 阈值不会造成问题，反而因候选池扩大增加命中概率