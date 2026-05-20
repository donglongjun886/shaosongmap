## ADDED Requirements

### Requirement: GitHub Actions 自动测试

系统 SHALL 在 `.github/workflows/test.yml` 提供 CI 工作流，在每次 push 和 pull request 时自动运行 pytest 测试套件。

工作流 MUST：
- 触发条件：push 到 main 分支、pull request 到 main 分支
- 运行环境：ubuntu-latest, Python 3.10
- 安装轻量依赖（排除 paddlepaddle/paddleocr，因为测试全部 mock OCR）
- 运行 `pytest tests/ -v` 并报告结果

#### Scenario: Push 触发测试

- **WHEN** 开发者 push 代码到 main 分支
- **THEN** GitHub Actions 自动运行测试，全部通过则 CI 标记为绿色

#### Scenario: PR 触发测试

- **WHEN** 开发者创建 pull request
- **THEN** CI 自动运行测试，测试失败则阻止合并

### Requirement: CI 轻量依赖文件

系统 SHALL 提供 `requirements-ci.txt`，包含 CI 运行所需的最小依赖集，不包括 paddlepaddle 和 paddleocr。

#### Scenario: CI 快速安装依赖

- **WHEN** CI workflow 执行 `pip install -r requirements-ci.txt`
- **THEN** 安装在 30 秒内完成，总依赖体积 < 200MB
