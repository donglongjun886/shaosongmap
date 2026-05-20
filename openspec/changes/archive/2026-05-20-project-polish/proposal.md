## Why

项目即将公开作为技术展示，但缺少几个规范开源项目的标配：`.env.example` 模板、CI/CD 自动化测试、`pyproject.toml` 项目配置、仓库中存在 1.2MB 测试截图、README 缺少状态徽章。这些细节直接影响项目的专业印象。

## What Changes

- 新增 `.env.example`：环境变量模板，去掉真实 key
- 新增 `.github/workflows/test.yml`：GitHub Actions 自动测试，每次 push 运行 40 个测试
- 新增 `pyproject.toml`：项目元数据、Python 版本要求、pytest/ruff 配置
- 压缩 `test_screenshot.png`：从 1.2MB 缩到 50KB 以内
- 修改 `README.md`：顶部添加测试状态、Python 版本、License 徽章

## Capabilities

### New Capabilities
- `ci-pipeline`: GitHub Actions 自动化测试流水线，push/PR 时运行 pytest
- `project-config`: 项目级配置文件（`pyproject.toml` + `.env.example`），包含元数据、工具链配置和环境变量模板

### Modified Capabilities
- `project-readme`: 顶部新增 CI 状态徽章和项目信息徽章

## Impact

- `.env.example`: **新增**
- `.github/workflows/test.yml`: **新增**
- `pyproject.toml`: **新增**
- `test_screenshot.png`: **修改**（压缩）
- `README.md`: **修改**（徽章）
- `requirements.txt`: 可能调整（CI 区分核心依赖和 OCR 可选依赖）