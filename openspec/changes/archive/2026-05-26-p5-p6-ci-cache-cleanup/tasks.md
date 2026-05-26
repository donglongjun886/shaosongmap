## 1. CI 流水线增强

- [x] 1.1 lint / type-check / test 作业添加 Python 版本矩阵（3.10, 3.11, 3.12）
- [x] 1.2 type-check 作业移除 `continue-on-error: true`，mypy 改为强制通过
- [x] 1.3 新增 pip-audit 作业，扫描依赖 CVE（informational，不阻塞）

## 2. CHGIS 数据缓存

- [x] 2.1 `_load_chgis_data()` 添加 `@functools.lru_cache(maxsize=1)` 装饰器
- [x] 2.2 运行现有测试确认缓存不破坏功能

## 3. CLAUDE.md 清理

- [x] 3.1 删除技术栈中的 `ORM: SQLAlchemy；数据库: PostgreSQL` 行
- [x] 3.2 预提交钩子链补充 detect-secrets（ruff format → ruff check → mypy → bandit → detect-secrets）
- [x] 3.3 分层架构描述改为 `routers → services`（移除 repositories）
- [x] 3.4 删除 `使用 repository 模式封装数据库操作，便于测试和复用。` 行
- [x] 3.5 删除 `数据库相关的测试必须使用事务回滚，确保测试原子性。` 行

## 4. 最终校验

- [x] 4.1 运行 `uv run pre-commit run --all-files` 全部门禁通过
- [x] 4.2 运行 `uv run pytest tests/ -v --cov=shaosongmap` 测试覆盖率达标