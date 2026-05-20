## ADDED Requirements

### Requirement: pyproject.toml 项目配置

系统 SHALL 在项目根目录提供 `pyproject.toml` 文件，包含项目元数据和工具链配置。

`pyproject.toml` MUST 包含：
- `[project]` 节：名称（shaosongmap）、版本（0.1.0）、Python 版本要求（>=3.10）
- `[tool.pytest.ini_options]` 节：pytest 默认运行参数
- 测试文件路径配置（testpaths = ["tests"]）

#### Scenario: 开发者查看项目元数据

- **WHEN** 开发者打开项目
- **THEN** 能在 `pyproject.toml` 中看到项目名称、版本和 Python 版本要求

#### Scenario: pytest 使用 pyproject.toml 配置

- **WHEN** 运行 `pytest` 不带参数
- **THEN** 自动发现 `tests/` 目录下的测试，使用 `pyproject.toml` 中的配置

### Requirement: .env.example 环境变量模板

系统 SHALL 在项目根目录提供 `.env.example` 文件，列出项目所需的所有环境变量及其用途说明，变量值使用占位符。

`.env.example` MUST 包含：
- `DEEPSEEK_API_KEY`：DeepSeek API 密钥
- `DEEPSEEK_BASE_URL`：DeepSeek API 地址（默认值）

#### Scenario: 新开发者配置环境

- **WHEN** 新开发者 clone 项目后
- **THEN** 复制 `.env.example` 为 `.env`，填入自己的 API Key 即可启动

### Requirement: 测试截图优化

系统 SHALL 将 `test_screenshot.png` 文件大小控制在 100KB 以内，通过降低分辨率实现而不影响 OCR 测试有效性。

#### Scenario: Clone 速度优化

- **WHEN** 开发者 clone 仓库
- **THEN** 测试截图文件不超过 100KB，不显著影响 clone 速度