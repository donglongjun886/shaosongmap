## MODIFIED Requirements

### Requirement: CLAUDE.md 开发规范文档

系统 SHALL 在项目根目录维护 `CLAUDE.md` 文件，作为 AI 辅助开发的规范指引，内容必须反映项目当前实际状态。

CLAUDE.md MUST：
- 技术栈描述与 `pyproject.toml` 实际依赖一致（不包含已移除的技术组件）
- 架构描述与项目实际分层一致：`routers` (接口层) → `services` (业务层)
- 预提交钩子列表与 `.pre-commit-config.yaml` 完全同步：ruff format → ruff check → mypy → bandit → detect-secrets
- 测试要求与 CI 配置一致（覆盖率和阈值）
- 不包含任何未实现的技术组件描述（如 SQLAlchemy、PostgreSQL、repository 模式、事务回滚）

#### Scenario: 新开发者阅读 CLAUDE.md

- **WHEN** 新开发者打开 `CLAUDE.md` 了解项目规范
- **THEN** 文档描述的技术栈与项目实际依赖完全一致，无已删除的持久化层描述

#### Scenario: 预提交钩子列表与配置一致

- **WHEN** 开发者对比 CLAUDE.md 与 `.pre-commit-config.yaml`
- **THEN** 两者的钩子列表完全相同，CLAUDE.md 包含 detect-secrets

### Requirement: 安装指令使用 uv

项目的安装指南 SHALL 使用 `uv sync` 作为依赖管理命令，替换 `pip install -r requirements.txt`。

README.md 的安装步骤 MUST：
- 使用 `uv sync` 安装项目依赖
- 使用 `.venv/bin/activate` 或 `uv run` 激活虚拟环境
- 不再引用 `requirements.txt`（可保留文件但标记为过时）

#### Scenario: 新贡献者按 README 安装

- **WHEN** 新开发者按 README 的安装指南执行 `uv sync`
- **THEN** 所有项目依赖和开发依赖正确安装，可立即启动服务
