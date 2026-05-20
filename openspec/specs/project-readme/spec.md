## Requirements

### Requirement: README 项目简介

系统 SHALL 在项目根目录提供 `README.md` 文件，包含项目名称、一句话描述和核心功能列表，使新访问者能在 30 秒内理解项目用途。

README MUST 包含：
- 项目名称和中文简介
- 核心功能列表（截图 OCR、战役文本提取、古地名匹配、地图渲染）
- 技术栈说明

#### Scenario: 首次访问者理解项目

- **WHEN** 访问者打开 GitHub 仓库首页
- **THEN** 能在 README 中看到项目名称、简介和功能列表，无需阅读源码即可了解项目

### Requirement: README 快速开始指南

系统 SHALL 在 README 中提供从零到运行的完整步骤。

快速开始 MUST 包含：
- 环境要求（Python 3.10+）
- 依赖安装命令
- 环境变量配置说明（DEEPSEEK_API_KEY）
- 启动命令
- 访问地址（http://localhost:8765）

#### Scenario: 新开发者成功启动项目

- **WHEN** 开发者按 README 步骤操作
- **THEN** 能在本地成功启动服务并在浏览器中看到功能界面

### Requirement: README 项目结构说明

系统 SHALL 在 README 中展示项目目录结构，标注关键文件和目录的用途。

#### Scenario: 开发者快速定位代码

- **WHEN** 开发者需要修改某个功能
- **THEN** 能通过项目结构说明快速找到对应的源码文件

### Requirement: README API 概览

系统 SHALL 在 README 中列出主要 API 端点及其用途，并在末尾包含「许可说明」章节，声明代码部分采用 MIT License，CHGIS 数据部分遵循学术使用限制。

#### Scenario: 前端开发者了解接口

- **WHEN** 前端开发者查看 README
- **THEN** 能看到所有 API 端点的路径、方法和简要说明

#### Scenario: 使用者了解许可条款

- **WHEN** 使用者查看 README 末尾
- **THEN** 能看到许可说明章节，区分代码（MIT）和数据（CHGIS 学术许可）