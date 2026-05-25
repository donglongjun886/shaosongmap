## MODIFIED Requirements

### Requirement: pyproject.toml 项目配置

系统 SHALL 在项目根目录提供 `pyproject.toml` 文件，包含项目元数据、依赖管理和工具链配置。

`pyproject.toml` MUST 包含：
- `[project]` 节：名称（shaosongmap）、版本（0.1.0）、Python 版本要求（>=3.10）、依赖列表
- `[dependency-groups]` 节：dev（开发工具集）和 test（CI 测试集）依赖分组
- `[tool.pytest.ini_options]` 节：pytest 运行参数和覆盖率配置
- `[tool.ruff]` 节：代码格式化和 Lint 规则配置
- `[tool.ruff.format]` 节：格式化参数（单引号、100 列宽）
- `[tool.ruff.lint]` 节：启用的规则集和排除目录
- `[tool.mypy]` 节：静态类型检查参数
- `[tool.coverage.run]` 和 `[tool.coverage.report]` 节：覆盖率配置
- `[tool.setuptools.packages.find]` 节：包发现配置

#### Scenario: 开发者查看项目配置

- **WHEN** 开发者打开 `pyproject.toml`
- **THEN** 能看到所有工具链配置集中在一个文件中，无需查阅多个配置文件

#### Scenario: uv 管理依赖

- **WHEN** 开发者运行 `uv sync`
- **THEN** uv 根据 `pyproject.toml` 和 `uv.lock` 安装所有项目依赖和开发依赖

## ADDED Requirements

### Requirement: .editorconfig 编辑器统一配置

系统 SHALL 在项目根目录提供 `.editorconfig` 文件，统一不同编辑器的缩进、换行符和字符编码设置。

`.editorconfig` MUST 配置：
- Python 文件：4 空格缩进，UTF-8 编码，LF 换行
- HTML/CSS/JS/JSON/YAML/Markdown 文件：2 空格缩进

#### Scenario: 不同编辑器打开同一文件

- **WHEN** 开发者分别用 VS Code 和 PyCharm 打开同一 Python 文件
- **THEN** 两者使用相同的缩进（4 空格）和换行符（LF），避免格式冲突
