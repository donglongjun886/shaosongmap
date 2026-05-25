## Purpose

预提交钩子链——在每次 git commit 时自动执行代码质量检查，确保进入仓库的代码符合项目规范。

## Requirements

### Requirement: pre-commit 钩子自动执行

系统 SHALL 在 `.pre-commit-config.yaml` 中配置预提交钩子链，在每次 `git commit` 时自动执行代码质量检查。钩子链 MUST 按以下顺序执行：

1. **ruff format** — 自动格式化代码，无需用户干预
2. **ruff check** — 检查代码质量违规项，自动修复可修复项
3. **mypy** — 静态类型检查，报告类型错误
4. **bandit** — 安全漏洞扫描

任何钩子失败 SHALL 阻止提交完成，用户 MUST 修复后方可提交。

#### Scenario: 提交包含格式问题的代码

- **WHEN** 用户 `git commit` 包含不符合 ruff 格式规范的代码
- **THEN** ruff format 自动修正格式，提交继续执行后续检查

#### Scenario: 提交包含 Lint 错误的代码

- **WHEN** 用户提交包含 `F841`（未使用变量）等可自动修复的 Lint 错误
- **THEN** ruff check 自动修复，提交继续

#### Scenario: 提交包含类型错误的代码

- **WHEN** 用户提交包含 mypy 检测到的类型不一致
- **THEN** 钩子报告错误并阻止提交，提示用户修复

#### Scenario: 提交包含安全漏洞的代码

- **WHEN** 用户提交包含 `subprocess.run(shell=True)` 等潜在安全风险
- **THEN** bandit 报告漏洞并阻止提交，提示用户确认或修复

### Requirement: 钩子配置可维护

pre-commit 配置 MUST 使用 `.pre-commit-config.yaml` 标准格式，所有钩子版本使用 `rev` 锁定。配置 MUST 包含 `minimum_pre_commit_version` 最低版本要求。

#### Scenario: 新开发者初始化钩子

- **WHEN** 新开发者 clone 项目后运行 `pre-commit install`
- **THEN** 所有钩子自动安装，后续每次 commit 自动触发