# CLAUDE.md：Python 项目开发规范

## 0. 通用行为准则
- 永远使用中文进行对话和注释，代码本身除外。
- 在动手前，复述你对任务的理解，并制定简要计划。
- 所有公开类和方法必须有详细的中文docstring。
- 完成一个功能单元后，为我生成单元测试和对应的提交信息。
- 绝不修改未被明确提及的文件，每次只做最小化修改。

## 1. 技术栈
- Python 3.10+
- 包管理: uv（依赖锁定 uv.lock，pip 仅作后备）
- Web 框架: FastAPI + Pydantic 数据校验
- ORM: SQLAlchemy；数据库: PostgreSQL
- 代码质量: ruff（格式化 + Lint，替代 black/isort/flake8）
- 静态类型: mypy（宽松起步，逐步收紧）
- 测试: pytest + pytest-cov（覆盖率阈值 70%）
- 安全扫描: bandit
- 预提交: pre-commit 钩子链（ruff format → ruff check → mypy → bandit）

## 2. 代码风格与架构
- 严格遵循 PEP8 和 PEP 257 规范。
- 项目采用分层架构：`routers` (接口层) -> `services` (业务层) -> `repositories` (数据层)。
- 禁止在 `routers` 中编写业务逻辑，使用 Pydantic 模型定义所有请求和响应。
- 使用 `repository` 模式封装数据库操作，便于测试和复用。
- 所有代码提交前自动执行 ruff format + ruff check + mypy + bandit。
- 行宽限制 100 列，使用单引号，isort 自动排序导入。

## 3. 开发工作流
- 首次克隆后运行 `uv sync` 安装所有依赖
- 激活 pre-commit：`uv run pre-commit install`
- 手动格式化：`uv run ruff format . && uv run ruff check . --fix`
- 手动类型检查：`uv run mypy app.py shaosongmap/`
- 运行测试：`uv run pytest tests/ -v --cov=shaosongmap`
- 安全扫描：`uv run bandit -r shaosongmap/ app.py -ll`

## 4. 测试要求
- 使用 `pytest` 编写所有测试，测试文件置于 `tests/` 目录，命名: `test_<模块名>.py`。
- 业务逻辑层 (`services`) 的测试覆盖率至少要达到 90%。
- 数据库相关的测试必须使用事务回滚，确保测试原子性。
- CI 覆盖率阈值 70%，低于阈值阻止合并。