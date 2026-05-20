## 1. 环境变量与配置

- [x] 1.1 创建 `.env.example`，包含 DEEPSEEK_API_KEY 和 DEEPSEEK_BASE_URL 模板
- [x] 1.2 创建 `pyproject.toml`，包含项目元数据和 pytest 配置

## 2. CI/CD

- [x] 2.1 创建 `requirements-ci.txt`，排除 paddlepaddle/paddleocr 的精简依赖
- [x] 2.2 创建 `.github/workflows/test.yml`，实现 push/PR 自动测试

## 3. 资源优化

- [x] 3.1 压缩 `test_screenshot.png` 至 100KB 以内

## 4. README 徽章

- [x] 4.1 在 README.md 顶部添加 CI 状态、Python 版本、License 徽章