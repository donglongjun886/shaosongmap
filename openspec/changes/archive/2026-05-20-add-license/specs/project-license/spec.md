## ADDED Requirements

### Requirement: MIT 开源许可

系统 SHALL 在项目根目录提供 `LICENSE` 文件，包含完整的 MIT License 文本，覆盖 `shaosongmap/`、`app.py`、`static/`、`scripts/`、`tests/` 目录中的所有代码文件。

#### Scenario: 访问者查看许可

- **WHEN** 访问者打开仓库首页或 LICENSE 文件
- **THEN** 能看到 MIT License 全文，明确代码部分可自由使用、修改、分发，仅需保留版权声明

### Requirement: CHGIS 数据许可声明

系统 SHALL 在 README 的「许可说明」章节中单独声明 `data/chgis_v6/chgis_v6_points.csv` 的许可限制，明确该数据遵循 CHGIS v6 学术使用条款（免费用于学术/个人用途，商业使用需联系 Harvard Fairbank Center for Chinese Studies）。

#### Scenario: 使用者了解数据许可差异

- **WHEN** 使用者阅读 README 许可说明章节
- **THEN** 能清楚区分代码（MIT）和数据（CHGIS 学术许可）的不同使用范围