## Why

当前项目的工程基础设施与 CLAUDE.md 承诺的分层架构、ruff 格式化等规范严重脱节——预提交钩子、静态类型检查、代码格式化、依赖锁定等 2026 年标准实践全部缺失，CI 仅跑 pytest 基础测试。在代码量突破 3500 行之前，必须打好地基。

## What Changes

- **BREAKING**: 将 pip 依赖管理迁移至 uv，使用 `uv.lock` 锁定依赖版本
- 引入 pre-commit 钩子链：ruff format → ruff check → mypy → bandit → detect-secrets
- 在 pyproject.toml 中配置 ruff（替代 black + isort + flake8，单一工具搞定）
- 在 pyproject.toml 中配置 mypy 严格类型检查
- 在 pyproject.toml 中配置 pytest-cov 覆盖率阈值
- 强化 CI 流程：lint → type check → test with coverage → security scan
- 添加 .editorconfig 统一编辑器设置
- 自动修复现有代码中的 ruff 违规项

## Capabilities

### New Capabilities

- `pre-commit-hooks`: 自动化预提交钩子链——代码格式化、质量检查、类型检查、安全检查在提交前自动执行，确保所有提交都通过质量门禁
- `code-quality-config`: ruff（代码格式+Lint）、mypy（静态类型检查）、bandit（安全扫描）的 pyproject.toml 集中配置

### Modified Capabilities

- `ci-pipeline`: CI 流程从单步 `pytest` 扩展为多阶段门禁——ruff check → mypy → pytest with coverage → bandit 安全扫描
- `project-config`: pyproject.toml 从仅含 setuptools + pytest 配置，扩展为包含 ruff、mypy、pytest-cov 的完整工程配置

## Impact

- `pyproject.toml` — 大幅扩展配置项（ruff、mypy、coverage、bandit）
- `requirements.txt` / `requirements-ci.txt` — 废弃，迁移至 `pyproject.toml` 的 `[dependency-groups]`
- `.github/workflows/test.yml` — 强化为多阶段门禁
- `.pre-commit-config.yaml` — 新增文件
- `.editorconfig` — 新增文件
- 所有 `.py` 文件 — 首次运行 ruff format 将产生统一格式化差异
- `CLAUDE.md` — 更新工具链说明以反映实际落地配置
