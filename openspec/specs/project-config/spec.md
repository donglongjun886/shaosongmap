## Requirements

### Requirement: pyproject.toml 项目配置

系统 SHALL 在项目根目录提供 `pyproject.toml` 文件，包含项目元数据、依赖管理和工具链配置。

`pyproject.toml` MUST 包含：
- `[project]` 节：名称（shaosongmap）、版本（0.1.0）、Python 版本要求（>=3.10）、依赖列表
- `[dependency-groups]` 节：dev（开发工具集）依赖分组
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

### Requirement: .editorconfig 编辑器统一配置

系统 SHALL 在项目根目录提供 `.editorconfig` 文件，统一不同编辑器的缩进、换行符和字符编码设置。

`.editorconfig` MUST 配置：
- Python 文件：4 空格缩进，UTF-8 编码，LF 换行
- HTML/CSS/JS/JSON/YAML/Markdown 文件：2 空格缩进

#### Scenario: 不同编辑器打开同一文件

- **WHEN** 开发者分别用 VS Code 和 PyCharm 打开同一 Python 文件
- **THEN** 两者使用相同的缩进（4 空格）和换行符（LF），避免格式冲突

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

### Requirement: CORS Origins 环境变量可配

系统 SHALL 通过 `CORS_ORIGINS` 环境变量配置允许的跨域来源，默认值为 `*`。

配置格式 MUST 为逗号分隔的域名列表：
- `CORS_ORIGINS=*`（默认）：允许所有来源
- `CORS_ORIGINS=https://shaosongmap.com,https://www.shaosongmap.com`：仅允许指定域名

#### Scenario: 开发环境默认全放通

- **WHEN** 未设置 `CORS_ORIGINS` 环境变量
- **THEN** `allow_origins` 为 `["*"]`，所有跨域请求均被允许

#### Scenario: 生产环境限制特定域名

- **WHEN** `CORS_ORIGINS` 设置为 `https://shaosongmap.com`
- **THEN** 仅来自此域名的跨域请求被允许

### Requirement: 安装指令使用 uv

项目的安装指南 SHALL 使用 `uv sync` 作为依赖管理命令，替换 `pip install -r requirements.txt`。

README.md 的安装步骤 MUST：
- 使用 `uv sync` 安装项目依赖
- 使用 `.venv/bin/activate` 或 `uv run` 激活虚拟环境
- 不再引用 `requirements.txt`（可保留文件但标记为过时）

#### Scenario: 新贡献者按 README 安装

- **WHEN** 新开发者按 README 的安装指南执行 `uv sync`
- **THEN** 所有项目依赖和开发依赖正确安装，可立即启动服务