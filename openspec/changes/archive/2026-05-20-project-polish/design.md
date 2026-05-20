## Context

项目缺少 CI/CD、`.env.example`、`pyproject.toml` 等规范开源项目的标配文件，README 缺少徽章，`test_screenshot.png` 达 1.2MB 增加 clone 负担。

## Goals / Non-Goals

**Goals:**
- GitHub Actions 实现 push/PR 自动测试
- `.env.example` 提供环境变量模板
- `pyproject.toml` 提供项目元数据和工具配置
- 压缩测试截图到 50KB 以内
- README 顶部添加状态徽章

**Non-Goals:**
- 不做 CD（自动部署）
- 不加 pre-commit hooks
- 不加 codecov 等高级 CI 功能

## Decisions

### 1. CI 跳过 OCR 依赖

**选择**: CI 安装轻量依赖（fastapi, pydantic, openai, numpy, Pillow, pytest 等），跳过 paddlepaddle 和 paddleocr。

**理由**: 所有 40 个测试均 mock 了 OCR 调用，PaddleOCR 是懒加载（`_init_ocr()` 内 import），测试中从未触发。paddlepaddle 包体积巨大（>1GB），跳过可让 CI 在 30 秒内完成。

**实现**: 创建 `requirements-ci.txt`，排除 paddlepaddle/paddleocr。

### 2. pyproject.toml 结构

**选择**: 最小化配置，包含：
- `[project]` — 名称、版本、Python 版本要求
- `[tool.pytest.ini_options]` — pytest 默认参数
- `[tool.ruff]` — 代码风格规则（预留）

**理由**: 不过度设计，只放当前实际使用的配置。

### 3. 徽章

**选择**: shields.io 动态徽章：
- CI 状态：GitHub Actions workflow status badge
- Python 版本：静态 3.10+
- License：静态 MIT

### 4. 测试截图处理

**选择**: 用 Pillow 缩小到宽度 400px + 灰度化，目标 <50KB。

**理由**: OCR 测试只需要有文字，不需要高清彩色。1.2MB → 30KB 对 OCR 识别效果影响极小。

## Risks / Trade-offs

- CI 跳过 PaddlePaddle → 无法测 OCR 真实调用 → 接受，OCR 测试主要测试清洗逻辑，模型调用由 PaddleOCR 团队保证