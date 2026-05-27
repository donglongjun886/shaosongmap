## Requirements

### Requirement: GitHub Actions 自动测试

系统 SHALL 在 `.github/workflows/test.yml` 提供 CI 工作流，在每次 push 和 pull request 时自动执行五阶段质量门禁。

工作流 MUST：
- 触发条件：push 到 main 分支、pull request 到 main 分支
- 运行环境：ubuntu-latest, Python 3.10
- 使用 uv 安装依赖（`uv sync --group dev`）
- 按顺序执行五个阶段：

**Stage 1 - Lint：**
- `ruff check .` 检查代码质量
- 不可自动修复的违规项阻止流程继续

**Stage 2 - Type Check：**
- `mypy app.py shaosongmap/` 静态类型检查
- 类型错误强制阻塞流程（不再使用 `continue-on-error`）

**Stage 3 - Test：**
- `pytest tests/ -v --cov=shaosongmap --cov-fail-under=70`
- 覆盖率低于 70% 则失败

**Stage 4 - Security：**
- `bandit -r shaosongmap/ app.py` 安全扫描
- 发现高危漏洞阻止流程

**Stage 5 - Audit：**
- `pip-audit` 扫描依赖包已知 CVE
- 仅报告不阻塞（informational），供开发者审阅

#### Scenario: Push 触发 CI

- **WHEN** 开发者 push 代码到 main 分支
- **THEN** GitHub Actions 自动运行五阶段门禁，全部通过则标记为绿色

#### Scenario: PR Lint 阶段失败

- **WHEN** 开发者创建 PR 包含 ruff 无法自动修复的违规项
- **THEN** CI 在 Stage 1 失败，阻止后续阶段执行，提示具体文件和违规规则

#### Scenario: PR 覆盖率未达标

- **WHEN** 开发者创建 PR 但新增代码未充分测试，覆盖率低于 70%
- **THEN** CI 在 Stage 3 失败，报告当前覆盖率与阈值差距

#### Scenario: PR 安全扫描告警

- **WHEN** 开发者提交包含 `shell=True` 的 subprocess 调用
- **THEN** CI 在 Stage 4 标记为失败，报告漏洞类型和文件位置

#### Scenario: mypy 类型错误阻塞 PR

- **WHEN** 开发者提交包含类型错误的代码
- **THEN** CI Stage 2 失败并阻止合并，不再被静默跳过

#### Scenario: pip-audit 发现 CVE

- **WHEN** 项目依赖包含已知 CVE 漏洞
- **THEN** CI Stage 5 报告漏洞详情但不阻塞流程，开发者可审阅后决定是否修复

### Requirement: CI 依赖管理

系统 SHALL 通过 pyproject.toml 的 `[dependency-groups]` 管理 CI 依赖，废弃 `requirements-ci.txt`。

uv 依赖组 MUST 区分：
- `[dependency-groups].dev`：开发工具（ruff、mypy、pytest、pytest-cov、bandit、pre-commit）

CI 工作流中 SHALL 使用 `uv sync --group dev` 安装所有质量工具。

#### Scenario: CI 通过 uv 安装依赖

- **WHEN** CI workflow 执行 `uv sync --group dev`
- **THEN** 安装所有开发和测试依赖，无需独立 requirements-ci.txt