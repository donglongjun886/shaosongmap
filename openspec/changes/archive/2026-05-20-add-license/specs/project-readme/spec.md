## MODIFIED Requirements

### Requirement: README API 概览

系统 SHALL 在 README 中列出主要 API 端点及其用途，并在末尾包含「许可说明」章节，声明代码部分采用 MIT License，CHGIS 数据部分遵循学术使用限制。

#### Scenario: 前端开发者了解接口

- **WHEN** 前端开发者查看 README
- **THEN** 能看到所有 API 端点的路径、方法和简要说明

#### Scenario: 使用者了解许可条款

- **WHEN** 使用者查看 README 末尾
- **THEN** 能看到许可说明章节，区分代码（MIT）和数据（CHGIS 学术许可）