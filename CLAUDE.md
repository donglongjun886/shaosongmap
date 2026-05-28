# CLAUDE.md：Python 项目开发规范

## 0. 通用行为准则
- 永远使用中文进行对话和注释，代码本身除外。
- 在动手前，复述你对任务的理解，并制定简要计划。
- 所有公开类和方法必须有详细的中文docstring。
- 完成一个功能单元后，为我生成单元测试和对应的提交信息。
- 绝不修改未被明确提及的文件，每次只做最小化修改。

## 1. 技术栈
- Python 3.10+
- 包管理: uv（依赖锁定 uv.lock，pip 仅作后备）
- Web 框架: FastAPI + Pydantic 数据校验
- 代码质量: ruff（格式化 + Lint，替代 black/isort/flake8）
- 静态类型: mypy（宽松起步，逐步收紧）
- 测试: pytest + pytest-cov（覆盖率阈值 70%）
- 预提交: pre-commit 钩子链（ruff format → ruff check → mypy）

## 2. 代码风格与架构
- 严格遵循 PEP8 和 PEP 257 规范。
- 项目采用分层架构：`routers` (接口层) -> `services` (业务层)。
- 禁止在 `routers` 中编写业务逻辑，使用 Pydantic 模型定义所有请求和响应。
- 所有代码提交前自动执行 ruff format + ruff check + mypy。
- 行宽限制 100 列，使用单引号，isort 自动排序导入。

## 3. 开发工作流
- 首次克隆后运行 `uv sync` 安装所有依赖
- 激活 pre-commit：`uv run pre-commit install`
- 手动格式化：`uv run ruff format . && uv run ruff check . --fix`
- 手动类型检查：`uv run mypy app.py shaosongmap/`
- 运行测试：`uv run pytest tests/ -v --cov=shaosongmap`
## 4. 测试要求
- 使用 `pytest` 编写所有测试，测试文件置于 `tests/` 目录，命名: `test_<模块名>.py`。
- 业务逻辑层 (`services`) 的测试覆盖率至少要达到 90%。
- CI 覆盖率阈值 70%，低于阈值阻止合并。

## 5. 多模型协作（MCP 工具调用规则）

本项目采用"主控 Agent + 专业工具"架构。主控模型 DeepSeek V4 Pro 负责意图理解、OpenSpec 设计
和复杂算法实现，以下专业能力通过 MCP 工具调用外部模型：

### 工具清单

| 工具 | 底层模型 | 用途 | 触发条件 |
|------|---------|------|---------|
| `generate_frontend` | Qwen-VL-Max | 看图生成视觉骨架代码（皮） | 前端新功能/改布局，有截图参考时 |
| `review_code` | DeepSeek-reasoner | 异源审查 | 写完一段完整功能后 |
| `run_e2e_test` | Playwright+Qwen-VL | 自动化自测 | 前端改动后验证渲染效果 |
| `analyze_ui` | Qwen-VL-Max | 人工视觉诊断 | 用户发现自测结果有问题，贴截图深入分析 |

### 前端开发"皮/骨"分工

Qwen-VL-Max 画"皮"——负责还原"长什么样"：
- HTML 结构、CSS 布局
- 古风配色（#f5f0e1 背景 / #8b4513 棕色系 / #c41e3a 朱砂红）、Noto Serif SC 字体渲染
- Canvas 2D 兵牌/旗帜/图标基础绘制
- 基础 UI 交互骨架

DeepSeek 主控画"骨"——负责实现"怎么动"：
- 贝塞尔曲线 / 毛笔笔锋粗细变化算法
- MapLibre GL JS 坐标矩阵变换
- Canvas 与底图缩放同步（rAF + 脏标记）
- 复杂状态机管理

> generate_frontend 遇到复杂算法时用占位函数 + 注释标注，留给主控后续注入。不要越界去写"骨"。

### 前端开发完整流程

```
截图/需求 → generate_frontend(Qwen-VL)→ 视觉骨架代码(皮)
                                            │
                                    主控 DeepSeek 审查骨架 → 注入复杂逻辑(骨)
                                            │
                                    run_e2e_test 自动化自测
                                            │
                            pass ←──→ fail → 用户发现视觉问题
                                                   │
                                           贴截图 → analyze_ui 诊断
```

### 强制规则

1. 前端新增功能或有参考截图时，**必须**先调 `generate_frontend` 获取视觉骨架，再由主控注入复杂逻辑
2. 写完一段完整功能后，**必须**调用 `review_code` 做异源审查
3. 前端改动完成后，**必须**调用 `run_e2e_test` 验证
4. 用户贴截图诊断视觉问题时，**必须**调用 `analyze_ui`，严禁主控模型"猜测"图片内容
5. 同一工具连续返回 error **2 次必须停止**，向用户报告，禁止无限重试
6. 修改了 `mcp_server/qwen_mcp_server.py` 源码后，**必须提醒用户重启 Claude Code** 才能生效（MCP 进程不会热更新）

### 设计原则

- Qwen-VL 画皮，DeepSeek 画骨，DeepSeek-reasoner 审查 —— 永远保持异源
- MCP 工具返回的是结构化摘要，不是原始日志
- 工具层内部处理瞬态重试（1 次），只有业务级错误才暴露给主控