## MODIFIED Requirements

### Requirement: 启动时配置完整性校验

系统 SHALL 在应用启动时通过 pydantic-settings 对所有必需配置项进行校验，缺失必填项时拒绝启动。

配置模型 MUST 包含：

| 字段 | 类型 | 必填 | 默认值 |
|------|------|------|--------|
| `deepseek_api_key` | `str` | 是 | — |
| `deepseek_base_url` | `str` | 否 | `https://api.deepseek.com` |
| `dashscope_api_key` | `str` | 否 | `""` |
| `cors_origins` | `list[str]` | 否 | `["*"]` |
| `log_level` | `str` | 否 | `"INFO"` |
| `log_format` | `str` | 否 | `"text"` |

配置加载优先级 MUST 为：环境变量 > `.env` 文件 > 硬编码默认值。

`.env.example` 文件 SHALL 包含上述所有字段，按类别分组并附中文注释，新贡献者复制为 `.env` 并填入必填项即可启动。

#### Scenario: 必需配置缺失时拒绝启动

- **WHEN** 未设置 `DEEPSEEK_API_KEY` 环境变量且 `.env` 文件无此配置
- **THEN** 应用启动失败，输出明确错误信息：`缺少必需配置: DEEPSEEK_API_KEY`

#### Scenario: 配置完整时正常启动

- **WHEN** `DEEPSEEK_API_KEY` 已在 `.env` 文件中正确配置
- **THEN** 应用正常启动，`app.state.settings` 可访问完整配置对象

#### Scenario: 模块从 config 单例读取配置

- **WHEN** `extractor.py` 需要 DeepSeek API key
- **THEN** 从 `shaosongmap.config.settings` 单例读取，而非在函数内调用 `os.getenv`

#### Scenario: .env.example 覆盖所有配置项

- **WHEN** 新贡献者查看 `.env.example`
- **THEN** 文件包含 `DEEPSEEK_API_KEY`、`DASHSCOPE_API_KEY`、`CORS_ORIGINS`、`LOG_LEVEL`、`LOG_FORMAT` 等所有字段，并附中文注释说明用途
