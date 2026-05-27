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

本项目采用"主控 Agent + 专业工具"架构。主控模型 DeepSeek V4 Pro 负责意图理解和代码生成，
以下专业能力通过 MCP 工具调用外部模型：

| 场景 | 工具 | 底层模型 | 触发条件 |
|------|------|---------|---------|
| 看图/截图分析 | `analyze_ui` | Qwen-VL-Max | 用户贴图、UI 审查、设计参考提取 |
| 代码审查 | `review_code` | DeepSeek-reasoner | 写完代码后自审、PR 前检查 |
| 前端自测 | `run_e2e_test` | Playwright+Qwen-VL | 前端改动后验证渲染效果 |

**强制规则：**
1. 涉及图片分析时，**必须**调用 `analyze_ui`，严禁用主控模型"猜测"图片内容
2. 写完一段完整功能后，**必须**调用 `review_code` 做异源审查
3. 前端改动完成后，**建议**调用 `run_e2e_test` 验证
4. 同一工具连续返回 error **2 次必须停止**，向用户报告，禁止无限重试
5. 修改了 `mcp/qwen_mcp_server.py` 源码后，**必须提醒用户重启 Claude Code** 才能生效（MCP 进程不会热更新）

**设计原则：**
- 主控 DeepSeek 写代码，Qwen 看图，DeepSeek-reasoner 审查 —— 永远保持异源
- MCP 工具返回的是结构化摘要，不是原始日志
- 工具层内部处理瞬态重试（1次），只有业务级错误才暴露给主控