# Secrets Scanning 敏感信息扫描

## Purpose

通过 pre-commit 钩子自动检测代码中的硬编码密钥、token 等敏感信息，防止误提交。

## Requirements

### Requirement: pre-commit detect-secrets 集成

项目的 pre-commit 钩子配置 SHALL 包含 `detect-secrets` 扫描步骤。

配置 MUST：
- 在 `.pre-commit-config.yaml` 中添加 `detect-secrets` hook
- 使用稳定版本（>=1.5.0）
- 启用基线文件 `.secrets.baseline`，允许审计后排除已知误报
- 扫描阶段置于 ruff 和 mypy 之后（secrets 扫描优先级最高，阻断提交）

#### Scenario: 检测到硬编码密钥时阻断提交

- **WHEN** 开发者在代码中添加了类似 `API_KEY=sk-abc123` 的行并尝试提交
- **THEN** `detect-secrets` hook 检测到并阻止提交，提示文件路径和行号

#### Scenario: 基线中的已知误报不阻断

- **WHEN** 代码中包含已在 `.secrets.baseline` 中审计并标记为误报的字符串
- **THEN** `detect-secrets` hook 允许提交通过

#### Scenario: 正常代码不受影响

- **WHEN** 代码不包含任何疑似密钥的字符串
- **THEN** `detect-secrets` hook 通过，不增加额外耗时