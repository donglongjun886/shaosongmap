## Context

当前项目约 3558 行 Python 代码，处于快速增长期（今日 6 次提交，~2300 行变更）。工程基础设施现状：

- **依赖管理**：pip + requirements.txt，无锁定文件，CI/本地两套文件
- **代码质量**：CLAUDE.md 声明用 ruff 但未配置，无法自动格式化或 Lint
- **类型检查**：无 mypy 配置，纯动态类型
- **CI**：仅 `pytest` 一步，无质量门禁
- **预提交**：无，全靠手动检查

目标是在代码量突破 10000 行之前建立自动化的质量保障体系。

## Goals / Non-Goals

**Goals:**
- 用 uv 替代 pip 作为包管理器和虚拟环境管理工具
- 搭建 pre-commit 钩子链，提交前自动 lint + format + type check + security scan
- 在 pyproject.toml 中集中配置所有质量工具（ruff、mypy、pytest-cov）
- CI 流程从单步测试扩展为四阶段门禁
- 自动修复现有代码的格式违规项

**Non-Goals:**
- 不拆分层架构（app.py 拆 routers/services 留到后续变更）
- 不追求 100% mypy 覆盖（先宽松起步，逐步收紧）
- 不引入第三方 SaaS 质量服务（Codecov、SonarCloud 等）

## Decisions

### 1. 用 uv 而非 Poetry

**选择**：uv  
**替代方案**：Poetry、PDM、pip-tools

| 维度 | uv | Poetry | pip-tools |
|------|-----|--------|-----------|
| 安装速度 | 极快 (Rust) | 慢 (Python) | 慢 (pip) |
| 依赖解析 | 极快 (Rust) | 慢 | 慢 |
| 锁文件 | uv.lock (跨平台) | poetry.lock | requirements.txt |
| PyPI 兼容 | 完全 | 有时卡住 | 完全 |
| 虚拟环境 | 内置 | 内置 | 需手动 |
| 团队心智 | 新兴但快速增长 | 成熟 | 老旧 |

选 uv 的核心原因：2026 年已是 Python 生态事实标准之一，Rust 实现带来 10-100x 速度提升，且与 pip 工作流无缝兼容。项目当前无复杂依赖，迁移风险极低。

### 2. ruff 统一替代 black + isort + flake8

**选择**：ruff（单一工具）  
**替代方案**：black + isort + flake8 三件套

ruff 优势：
- 一个工具搞定格式化和 Lint，配置集中
- Rust 实现，速度比 flake8 快 10-100x
- 规则与 flake8 兼容，内置 isort、pyupgrade 等规则集
- pre-commit 中只需 2 个 hook（format + check），而非 4-5 个

### 3. mypy 宽松起步策略

**选择**：`strict = false`，选配关键规则  
**替代方案**：`strict = true` 全面类型标注

项目 3500+ 行代码没有任何类型标注，strict 模式会产生数百条错误。采取逐步策略：
- 开启 `disallow_untyped_defs = false`（允许无类型函数）
- 开启 `warn_return_any = true`、`warn_unused_ignores = true`
- 后续变更逐步收紧

### 4. 依赖锁定策略

**选择**：uv.lock 锁定全量依赖，pyproject.toml 用 `[dependency-groups]` 区分 dev/test  
**替代方案**：保持 requirements.txt

uv.lock 提供：
- 确定性构建（所有 transitive deps 精确版本）
- 跨平台（Linux CI + macOS 本地）
- CI 中 `uv sync --group test` 替代 `pip install -r requirements-ci.txt`

### 5. CI 多阶段门禁

```
Stage 1: lint     → ruff check (不通过则失败)
Stage 2: type     → mypy (不通过则失败)
Stage 3: test     → pytest --cov --cov-fail-under=70
Stage 4: security → bandit
```

先易后难：如果格式都不对，没理由继续跑测试。

## Risks / Trade-offs

- **[风险] ruff format 首次运行产生大量 diff** → 单独提交一次 `style: ruff format 全局格式化`，与功能变更隔离
- **[风险] mypy 可能暴露大量类型问题** → 宽松起步，不阻塞 CI，后续逐步收紧；暂时设为 `continue-on-error: true` 在 CI 中告警但不失败
- **[风险] uv 团队其他成员不熟悉** → 目前是个人项目，影响为零
- **[权衡] bandit 可能产生误报** → 仅扫描 `app.py` 和 `shaosongmap/`，排除 `tests/`
