## Why

P5（CI 增强）和多版本兼容性缺口尚未闭合——当前 CI 仅在 Python 3.10 上测试，mypy 失败被 `continue-on-error` 静默忽略，且缺少依赖漏洞扫描。P6 的 CHGIS 数据每次调用都重新解析 CSV，存在不必要的 I/O 开销。同时 CLAUDE.md 仍残留已删除的持久化层描述，影响新人理解。

## What Changes

- **CI 矩阵化**：test/lint/type-check 作业增加 Python 3.10 / 3.11 / 3.12 矩阵
- **mypy 强制通过**：移除 `continue-on-error: true`，类型错误会阻塞 PR
- **pip-audit 漏洞扫描**：新增 CI job，扫描依赖已知 CVE
- **CHGIS 数据缓存**：`_load_chgis_data()` 添加 `@functools.lru_cache`，同一进程内仅加载一次
- **CLAUDE.md 清理**：删除 SQLAlchemy/PostgreSQL/repository/事务回滚等 4 处持久化描述，补齐 detect-secrets 钩子

## Capabilities

### New Capabilities
<!-- 本次不引入新 capability，全部为修改既有规范 -->

### Modified Capabilities
- `ci-pipeline`: CI 矩阵（3 个 Python 版本）、mypy 改为强制、新增 pip-audit 作业
- `chgis-data-pipeline`: CHGIS CSV 加载增加 LRU 缓存，优化重复 I/O
- `project-config`: CLAUDE.md 删除持久化层描述、补齐 detect-secrets 钩子

## Impact

- `.github/workflows/test.yml`：矩阵改造 + 新 job + 移除 continue-on-error
- `shaosongmap/geocoder.py`：`_load_chgis_data` 加 `@lru_cache(maxsize=1)`
- `CLAUDE.md`：5 行编辑（4 处删除 + 1 处修正）