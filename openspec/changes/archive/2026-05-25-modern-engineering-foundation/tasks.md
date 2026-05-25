## 1. uv 迁移与依赖管理

- [x] 1.1 安装 uv 并初始化项目依赖（`uv add` 将 requirements.txt 迁移到 pyproject.toml）
- [x] 1.2 在 pyproject.toml 中配置 `[dependency-groups]`（dev 和 test 分组）
- [x] 1.3 生成 `uv.lock` 锁文件

## 2. pyproject.toml 工具链配置

- [x] 2.1 添加 `[tool.ruff]` 配置（format 单引号+100列宽，lint 规则集 E/F/I/UP/B/SIM）
- [x] 2.2 添加 `[tool.mypy]` 配置（宽松起步，Python 3.10，关键警告开启）
- [x] 2.3 添加 `[tool.coverage]` 配置（排除 tests/，阈值 70%）
- [x] 2.4 更新 `[tool.pytest.ini_options]` 添加覆盖率默认参数

## 3. 预提交钩子

- [x] 3.1 创建 `.pre-commit-config.yaml`，配置 ruff format → ruff check → mypy → bandit 四个钩子
- [x] 3.2 运行 `pre-commit install` 安装钩子

## 4. 编辑器配置

- [x] 4.1 创建 `.editorconfig`（Python 4 空格，HTML/CSS/JS/JSON/YAML 2 空格，UTF-8 + LF）

## 5. 代码格式化

- [x] 5.1 运行 `ruff format .` 对全项目 Python 文件执行首次统一格式化
- [x] 5.2 运行 `ruff check . --fix` 自动修复可修复的 Lint 违规

## 6. CI 门禁强化

- [x] 6.1 更新 `.github/workflows/test.yml`：安装 uv → sync dev deps → 四阶段门禁
- [x] 6.2 废弃 `requirements-ci.txt`（功能由 pyproject.toml dependency-groups 替代）

## 7. CLAUDE.md 更新

- [x] 7.1 更新 CLAUDE.md 技术栈章节，反映 uv + ruff + mypy 实际落地情况

## 8. 验证

- [x] 8.1 运行 `ruff check .` 确认零违规
- [x] 8.2 运行 `mypy app.py shaosongmap/` 确认配置生效（允许初期告警）
- [x] 8.3 运行 `pytest tests/ -v --cov=shaosongmap` 确认所有测试通过且覆盖率达标
- [x] 8.4 运行 `bandit -r shaosongmap/ app.py` 确认无高危漏洞
- [x] 8.5 运行 `pre-commit run --all-files` 确认所有钩子通过