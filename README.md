# 绍宋地图 (ShaosongMap)

[![Test](https://github.com/donglongjun886/shaosongmap/actions/workflows/test.yml/badge.svg)](https://github.com/donglongjun886/shaosongmap/actions/workflows/test.yml)
[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

> 让历史小说读者「边读边看地图」—— 输入历史文本，识别古地名并可视化。

针对《绍宋》等宋代历史小说读者，从历史文本中自动提取地名、人物与地点的关联、边界疆域等地理实体，匹配宋代古地名坐标，渲染为交互式地图。

## 功能特性

- **🧠 地理实体识别** — DeepSeek LLM 从历史文本提取地名列表、人物→地点关联、边界/疆域
- **🗺️ 古地名匹配** — 基于 CHGIS v6 的宋代地名数据，精确匹配经纬度坐标
- **🤖 LLM 推断兜底** — 虚构地名或极小地点交由 LLM 根据上下文推断近似坐标
- **🌏 交互式地图** — MapLibre GL JS + MapTiler topo-v2 底图，展示古地名和地理实体，可区分数据来源
- **✏️ 结果可编辑** — 提取结果面板支持增删改查，修改后可重新渲染地图
- **📡 SSE 进度推送** — 提取→匹配→渲染三阶段进度实时展示

## 技术栈

| 层级 | 技术 |
|------|------|
| 包管理 | uv |
| Web 框架 | FastAPI + Pydantic |
| AI 提取 | DeepSeek API (OpenAI 兼容) |
| 古地名数据 | CHGIS v6 (Harvard Dataverse) |
| 前端地图 | MapLibre GL JS + MapTiler |
| 代码质量 | ruff + mypy + bandit + pre-commit |
| 测试 | pytest + pytest-cov (66 个测试用例) |

## 快速开始

### 环境要求

- Python 3.10+
- [uv](https://docs.astral.sh/uv/)（推荐）或 pip

### 安装

```bash
git clone https://github.com/donglongjun886/shaosongmap.git
cd shaosongmap
uv sync
```

### 配置

创建 `.env` 文件，设置所需的环境变量：

```bash
# DeepSeek API（必需）
DEEPSEEK_API_KEY=your_key_here
DEEPSEEK_BASE_URL=https://api.deepseek.com

# MapTiler API Key（可选，用于 MapTiler 底图；不设置则回退到 OSM raster）
MAPTILER_API_KEY=your_key_here
```

### 启动

```bash
uv run python app.py
```

浏览器打开 http://localhost:8765

## 项目结构

```
shaosongmap/
├── app.py                     # FastAPI 应用入口
├── pyproject.toml             # 项目配置 + 开发依赖
├── shaosongmap/
│   ├── config.py              # 配置中心 (pydantic-settings)
│   ├── schemas.py             # Pydantic 请求/响应模型
│   ├── models.py              # 领域数据模型 (Place, Boundary, PersonPlace, GeoEntityExtract, GeoFeature)
│   ├── extractor.py           # DeepSeek LLM 地理实体提取
│   ├── geocoder.py            # CHGIS 精确匹配 + LLM 推断兜底
│   ├── utils.py               # 工具函数
│   ├── routers/               # 接口层
│   │   ├── extract.py         # /api/v1/extract SSE 流式路由
│   │   ├── health.py          # /api/v1/health + /api/v1/config
│   │   └── render.py          # /api/v1/render 重新渲染路由
│   └── services/              # 业务层
│       ├── pipeline.py        # 提取管道编排
│       ├── geo.py             # 地理计算（方向角/距离/偏移）
│       └── geojson.py         # GeoJSON 构建
├── static/
│   ├── index.html             # 前端 SPA (MapLibre GL 地图 + 编辑面板)
│   ├── css/map.css            # 地图样式
│   └── js/
│       ├── app.js             # 应用逻辑（面板交互、编辑、SSE）
│       ├── map.js             # 地图渲染核心（MapLibre GL JS + MapTiler）
│       └── utils.js           # 纯函数工具
├── scripts/
│   ├── build_chgis.py         # CHGIS v6 数据管线构建
│   ├── code_review.py         # 代码审查脚本
│   ├── vision.py              # Qwen-VL 视觉审查
│   ├── automate_review.py     # Playwright 自动化视觉审查
│   ├── describe.py            # 图片分析 (Qwen-VL)
│   ├── full_audit.py          # 全量审计
│   └── selftest.py            # 自测脚本
├── data/
│   └── chgis_v6/
│       └── chgis_v6_points.csv
└── tests/
    ├── conftest.py
    ├── test_api.py
    ├── test_api_render.py
    ├── test_api_sse.py
    ├── test_extractor.py
    ├── test_frontend_utils.py
    ├── test_geocoder.py
    └── test_geojson.py
```

## API 概览

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/extract` | 提交历史文本，SSE 流式返回地理实体提取+古地名匹配+地图数据 |
| POST | `/api/v1/render` | 提交编辑后的数据，重新地理编码和渲染 |
| GET | `/api/v1/health` | 健康检查 |
| GET | `/api/v1/config` | 获取前端配置（MapTiler API Key） |
| GET | `/` | 静态前端界面 |

### POST /api/v1/extract

```
Content-Type: application/json
Body: { "text": "岳飞率军自襄阳出发...", "dynasty": "南宋" }

Response: text/event-stream (SSE)
  event: progress → { "stage": "extract_done" }
  event: progress → { "stage": "geocode_done", "detail": "匹配古地名 (8 CHGIS + 2 LLM推断)" }
  event: progress → { "stage": "render_done" }
  event: result   → { "features": [...], "geojson": {...} }
```

### POST /api/v1/render

```
Content-Type: application/json
Body: { "places": [...], "boundaries": [...], "person_places": [...], "dynasty": "宋" }

Response: { "features": [...], "geojson": {...} }
```

## 开发

```bash
# Lint 检查
uv run ruff check .

# 代码格式化
uv run ruff format .

# 类型检查
uv run mypy app.py shaosongmap/

# 运行测试（含覆盖率报告）
PYTHONPATH=. uv run pytest tests/ -v --cov=shaosongmap

# 安全扫描
uv run bandit -r shaosongmap/ app.py

# 全量门禁
uv run pre-commit run --all-files
```

## 许可

本项目采用**双重许可**：

| 范围 | 许可 | 说明 |
|------|------|------|
| 代码（`shaosongmap/`、`app.py`、`static/`、`scripts/`、`tests/`） | [MIT License](LICENSE) | 可自由使用、修改、分发，仅需保留版权声明 |
| 数据（`data/chgis_v6/chgis_v6_points.csv`） | [CHGIS v6 学术许可](https://dataverse.harvard.edu/dataverse/chgis_v6) | 免费用于学术和个人用途；商业使用需联系 Harvard Fairbank Center for Chinese Studies |

CHGIS v6 数据版权归 &copy; Fairbank Center for Chinese Studies, Harvard University 所有。`data/chgis_v6/chgis_v6_points.csv` 是从 CHGIS v6 原始数据筛选衍生的子集，遵循原始数据的许可条款。
