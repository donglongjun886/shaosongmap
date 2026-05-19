cat > CLAUDE.md << 'EOF'
# CLAUDE.md：Python 项目开发规范

## 0. 通用行为准则
- 永远使用中文进行对话和注释，代码本身除外。
- 在动手前，复述你对任务的理解，并制定简要计划。
- 所有公开类和方法必须有详细的中文docstring。
- 完成一个功能单元后，为我生成单元测试和对应的提交信息。
- 绝不修改未被明确提及的文件，每次只做最小化修改。

## 1. 技术栈
- Python 3.10+
- 用 FastAPI 做 Web 框架，Pydantic 做数据校验。
- ORM: SQLAlchemy；数据库: PostgreSQL
- 测试: pytest；代码格式化: ruff

## 2. 代码风格与架构
- 严格遵循 PEP8 和 PEP 257 规范。
- 项目采用分层架构：`routers` (接口层) -> `services` (业务层) -> `repositories` (数据层)。
- 禁止在 `routers` 中编写业务逻辑，使用 Pydantic 模型定义所有请求和响应。
- 使用 `repository` 模式封装数据库操作，便于测试和复用。

## 3. 测试要求
- 使用 `pytest` 编写所有测试，测试文件置于 `tests/` 目录，命名: `test_<模块名>.py`。
- 业务逻辑层 (`services`) 的测试覆盖率至少要达到 90%。
- 数据库相关的测试必须使用事务回滚，确保测试原子性。
  EOF