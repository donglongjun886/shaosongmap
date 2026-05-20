## MODIFIED Requirements

### Requirement: README 项目简介

系统 SHALL 在项目根目录提供 `README.md` 文件，包含项目名称、一句话描述、状态徽章和核心功能列表，使新访问者能在 30 秒内理解项目用途。

README MUST 包含：
- 项目名称和中文简介
- **状态徽章**：CI 测试状态、Python 版本要求（3.10+）、License 类型
- 核心功能列表（截图 OCR、战役文本提取、古地名匹配、地图渲染）
- 技术栈说明

#### Scenario: 首次访问者理解项目

- **WHEN** 访问者打开 GitHub 仓库首页
- **THEN** 能在 README 顶部看到项目名称、徽章、简介和功能列表，快速了解项目状态和质量