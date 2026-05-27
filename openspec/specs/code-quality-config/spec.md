## Purpose

代码质量工具链集中配置——在 pyproject.toml 中统一管理 ruff（格式化+Lint）、mypy（静态类型检查）、pytest-cov（测试覆盖率）的参数。

## Requirements

### Requirement: ruff 统一代码格式化与 Lint

系统 SHALL 在 `pyproject.toml` 的 `[tool.ruff]` 节中集中配置 ruff，包括格式化规则和 Lint 规则集。ruff 配置 MUST：

- 目标 Python 版本设为 3.10
- `[tool.ruff.format]`：使用单引号，行宽 100 列
- `[tool.ruff.lint]`：启用 `E`（pycodestyle）、`F`（pyflakes）、`I`（isort）、`UP`（pyupgrade）、`B`（flake8-bugbear）、`SIM`（flake8-simplify）规则集
- 排除目录：`.venv/`、`__pycache__/`、`tests/`（测试文件免检部分规则）

#### Scenario: 运行 ruff format

- **WHEN** 用户在终端运行 `ruff format .`
- **THEN** 所有 Python 文件按照 pyproject.toml 中定义的格式规则统一格式化

#### Scenario: 运行 ruff check

- **WHEN** 用户在终端运行 `ruff check .`
- **THEN** ruff 检查所有已启用规则，报告违规项，自动修复可修复项

#### Scenario: CI 中 Lint 检查失败

- **WHEN** CI 中 `ruff check .` 发现不可自动修复的违规项
- **THEN** CI 工作流标记为失败，阻止合并

### Requirement: mypy 静态类型检查

系统 SHALL 在 `pyproject.toml` 的 `[tool.mypy]` 节中配置 mypy 静态类型检查。mypy 配置 MUST：

- 目标 Python 版本 3.10
- 启动阶段宽松：`disallow_untyped_defs = false`，`check_untyped_defs = true`
- 启用关键警告：`warn_return_any = true`，`warn_unused_ignores = true`，`warn_redundant_casts = true`
- 排除 `.venv/` 目录

#### Scenario: 本地运行 mypy

- **WHEN** 用户在终端运行 `mypy app.py shaosongmap/`
- **THEN** mypy 对项目代码执行类型检查，报告类型不一致

#### Scenario: CI 中 mypy 告警

- **WHEN** CI 中 `mypy` 发现类型问题
- **THEN** 工作流输出告警但不阻塞流程（初期宽松策略）

### Requirement: pytest-cov 测试覆盖率门禁

系统 SHALL 在 `pyproject.toml` 的 `[tool.pytest.ini_options]` 和 `[tool.coverage]` 节中配置测试覆盖率。配置 MUST：

- `[tool.coverage.run]`：源码目录为 `shaosongmap/`，排除 `tests/`
- `[tool.coverage.report]`：终端输出缺失行，排除 `app.py`（前端路由，暂不纳入）
- CI 中设置覆盖率阈值为 70%（`--cov-fail-under=70`）

#### Scenario: 本地运行覆盖率报告

- **WHEN** 用户运行 `pytest --cov=shaosongmap --cov-report=term-missing`
- **THEN** 终端展示每个文件的覆盖率百分比和未覆盖行号

#### Scenario: CI 覆盖率未达标

- **WHEN** CI 中测试覆盖率低于 70%
- **THEN** CI 工作流标记为失败，阻止合并

### Requirement: pre-commit 钩子自动执行

系统 SHALL 在 `.pre-commit-config.yaml` 中配置预提交钩子链，在每次 `git commit` 时自动按顺序执行：ruff format → ruff check → mypy → bandit。

任何钩子失败 SHALL 阻止提交完成，用户 MUST 修复后方可提交。

#### Scenario: 提交包含格式问题的代码

- **WHEN** 用户 `git commit` 包含不符合 ruff 格式规范的代码
- **THEN** ruff format 自动修正格式，提交继续执行后续检查

#### Scenario: 提交包含类型错误的代码

- **WHEN** 用户提交包含 mypy 检测到的类型不一致
- **THEN** 钩子报告错误并阻止提交，提示用户修复

#### Scenario: 新开发者初始化钩子

- **WHEN** 新开发者 clone 项目后运行 `pre-commit install`
- **THEN** 所有钩子自动安装，后续每次 commit 自动触发