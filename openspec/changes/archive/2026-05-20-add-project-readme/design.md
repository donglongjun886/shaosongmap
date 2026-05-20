## Context

项目已具备 MVP 功能（截图 OCR → 战役文本提取 → 古地名 geocoding → 地图渲染），代码分布在 `shaosongmap/`、`app.py`、`static/`、`scripts/`、`tests/` 中。目前缺少 README，新开发者需要阅读源码才能理解项目。

## Goals / Non-Goals

**Goals:**
- 提供项目简介和功能概述
- 列出技术栈和依赖要求
- 提供快速开始步骤（安装、配置、启动）
- 展示项目结构和关键文件说明
- 描述 API 端点

**Non-Goals:**
- 不写详细的 API 文档（后续可用 OpenAPI/Swagger）
- 不写贡献指南（后续可加 CONTRIBUTING.md）
- 不写多语言版本（仅中文）

## Decisions

### 1. README 内容结构

**选择**: 采用经典 OSS 项目 README 结构：
1. 项目名称与简介
2. 功能特性（配截图占位）
3. 技术栈
4. 快速开始（环境要求 → 安装 → 配置 → 启动）
5. 项目结构
6. API 概览
7. 开发命令

**理由**: 这种结构是 GitHub 项目事实标准，开发者最熟悉。

### 2. 语言选择

**选择**: 中文为主，代码/命令保持英文。

**理由**: 项目面向中文用户（处理中文古地名），且 CLAUDE.md 要求使用中文。

## Risks / Trade-offs

- README 内容可能随时间过时 → 关键信息（如 API 端点）保持简要，详细文档后续单独维护
