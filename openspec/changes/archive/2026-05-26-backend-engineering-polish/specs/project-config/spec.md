## ADDED Requirements

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