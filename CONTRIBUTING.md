# 贡献指南

欢迎贡献！本项目是 solo 开源项目，但非常乐意接受社区 PR。

## 环境搭建

```bash
git clone https://github.com/donglongjun886/shaosongmap.git
cd shaosongmap
uv sync
uv run pre-commit install
```

## 开发

```bash
uv run ruff check .          # Lint 检查
uv run ruff format .         # 代码格式化
uv run mypy app.py shaosongmap/  # 类型检查
uv run pytest tests/ -v      # 运行测试
```

## 提交 PR

1. Fork 仓库并创建分支
2. 代码变更 + 补充测试
3. 确保 `uv run pre-commit run --all-files` 和 `uv run pytest tests/ -v` 通过
4. 提交 PR，描述变更内容和原因

## 项目规范

- Python 3.10+，单引号，行宽 100 列
- 业务逻辑在 `services/`，路由层只做参数校验和调用
- 测试覆盖率不低于 70%
- 提交信息用中文