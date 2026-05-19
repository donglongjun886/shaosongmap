# ShaosongMap

## 项目简介

让历史小说读者「边读边看地图」——输入《绍宋》等历史小说的战役段落，自动生成标注双方兵力、行军路线和地形的古代地图。

## 技术栈

| 层级 | 技术 | 版本/备注 |
|------|------|-----------|
| 语言 | Python | 3.11+ |
| Web 框架 | FastAPI | 异步支持 + 自动 OpenAPI 文档 |
| LLM | DeepSeek API | 用于战役文本结构化提取 |
| 数据校验 | Pydantic | 请求/响应模型 |
| 地理数据 | CHGIS v6 | 中国历史地理信息系统，地名→坐标匹配 |
| 数据库 | PostgreSQL | 生产环境；MVP 阶段可暂缓引入 |
| ORM | SQLAlchemy | 中后期接入 |
| 测试 | pytest | 核心链路必须覆盖 |
| 代码格式化 | ruff | PEP8 + 排序 import |
| 前端（后期） | React + Mapbox GL JS | MVP 后引入，地图可视化 |

## 项目结构

```
shaosongmap/              # 主包
├── __init__.py
├── extractor.py          # 调用 DeepSeek API，从战役文本提取结构化 JSON
├── geocoder.py           # 古地名 → CHGIS v6 经纬度匹配
├── models.py             # Pydantic 数据模型（战役、兵力、行军路线等）
app.py                    # FastAPI 应用入口
scripts/
├── parse_cli.py          # CLI 脚本：输入文本 → 输出结构化 JSON/GeoJSON
tests/
├── test_extractor.py
├── test_geocoder.py
data/
├── chgis_v6/             # CHGIS v6 数据集（古地名 + 坐标）
```

## 领域上下文

- **《绍宋》**：以宋朝为背景的历史穿越小说，包含大量真实地名和战役描写
- **战役文本**：通常包含双方将领名、兵力数量、古地名（州县）、行军方向、地形描述
- **古地名问题**：同一地点在不同朝代可能有不同名称（如「东京」→ 开封府），需要 CHGIS 时间轴匹配
- **输出目标**：结构化 JSON 用于后续前端地图渲染，需包含 GeoJSON 格式的行军路线

## MVP 功能范围

1. 接收一段战役文本
2. 调用 DeepSeek API 提取：战役名称、参战双方、将领、兵力、古地名列表、行军路线描述
3. 通过 CHGIS v6 匹配古地名→经纬度
4. 返回结构化 JSON（含坐标和路线 GeoJSON）
5. 提供 CLI 入口 `scripts/parse_cli.py` 供手动验证

MVP 阶段的刻意简化：
- 不引入数据库（先用文件/内存）
- 不做前端（CLI 验证链路）
- 不处理多语言
- 地形数据由 CHGIS 提供基础信息，不做高精度地形渲染

## 关键架构决策

1. **地名坐标用 CHGIS 匹配，而非纯 AI 生成**：LLM 幻觉会导致坐标不准，CHGIS v6 是学术界公认的中国历史地理数据集，经纬度可靠
2. **先用 CLI 验证核心链路，再加 API 和前端**：核心提取+匹配链路是价值关键，先保证输出质量再扩展交付形式
3. **选择 FastAPI**：异步支持适合 LLM API 调用，自动生成的 Swagger 文档方便后续前端对接

## 代码规范

见根目录 `CLAUDE.md`，核心要点：
- 注释与对话使用中文，代码用英文
- 分层架构：routers → services → repositories（MVP 阶段可合并 service 与 repo 层）
- 所有公开类和方法必须有中文 docstring
- 用 Pydantic 定义所有数据结构
- 测试覆盖率目标：业务层 ≥ 90%