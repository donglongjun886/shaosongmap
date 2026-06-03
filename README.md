# 绍宋地图 (ShaosongMap)

[![Test](https://github.com/donglongjun886/shaosongmap/actions/workflows/test.yml/badge.svg)](https://github.com/donglongjun886/shaosongmap/actions/workflows/test.yml)
[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

> 让历史小说读者「边读边看地图」—— 输入历史文本，识别古地名并可视化。

针对《绍宋》等宋代历史小说读者，从历史文本中自动提取地名、人物与地点的关联、边界疆域等地理实体，匹配宋代古地名坐标，渲染为交互式地图。

## 功能特性

- **🧠 地理实体识别** — DeepSeek LLM 从历史文本提取地名列表、人物→地点关联、边界/疆域、战役尺度
- **🗺️ 古地名匹配** — 基于 CHGIS v6 的宋代地名数据，精确匹配经纬度坐标
- **🤖 LLM 推断兜底** — 虚构地名或极小地点交由 LLM 根据上下文推断近似坐标
- **🌏 交互式地图** — MapLibre GL JS + MapTiler 底图，三层 Canvas 渲染（地形/路线/部队），可区分数据来源
- **✏️ 结果可编辑** — 提取结果面板支持增删改查，修改后可重新渲染地图
- **🏗️ 多模型协作** — DeepSeek（提取）+ Qwen3.7-Max（设计审查）+ Qwen-VL（视觉诊断）+ DeepSeek-reasoner（代码审查）

## 技术栈

| 层级 | 技术 |
|------|------|
| 包管理 | uv |
| Web 框架 | FastAPI + Pydantic |
| AI 提取 | DeepSeek API (OpenAI 兼容) |
| AI 审查 | Qwen3.7-Max（设计审查）、Qwen-VL-Max（视觉诊断）、DeepSeek-reasoner（代码审查） |
| OCR | PaddleOCR 3.x |
| 古地名数据 | CHGIS v6 (Harvard Dataverse) |
| 前端地图 | MapLibre GL JS + Canvas 2D 三层渲染 |
| 前端风格 | roughjs（手绘风格） |
| 速率限制 | slowapi |
| 部署 | Docker + docker-compose |
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

# 阿里云 DashScope API Key（可选，用于 OCR 识别）
DASHSCOPE_API_KEY=

# MapTiler API Key（可选，用于 MapTiler 底图；不设置则回退到 OSM raster）
MAPTILER_KEY=your_key_here

# CORS 允许的源站列表（可选，逗号分隔，默认允许所有）
CORS_ORIGINS=*

# 日志级别（可选）：DEBUG / INFO / WARNING / ERROR
LOG_LEVEL=INFO

# 日志格式（可选）：text（可读格式）/ json（结构化日志）
LOG_FORMAT=text
```

### 启动

```bash
uv run uvicorn app:app --host 0.0.0.0 --port 8765
```

浏览器打开 http://localhost:8765

或使用 Docker 启动：

```bash
docker compose up -d
```

## 项目结构

```
shaosongmap/
├── app.py                     # FastAPI 应用入口（路由挂载、中间件、配置端点）
├── pyproject.toml             # 项目配置 + 开发依赖
├── Dockerfile                 # Docker 镜像构建
├── docker-compose.yml         # Docker 编排
├── shaosongmap/
│   ├── config.py              # 配置中心 (pydantic-settings)
│   ├── schemas.py             # Pydantic 请求/响应模型
│   ├── models.py              # 领域数据模型 (Place, Boundary, PersonPlace, GeoEntityExtract, GeoFeature)
│   ├── extractor.py           # DeepSeek LLM 地理实体提取
│   ├── geocoder.py            # CHGIS 精确匹配 + LLM 推断兜底
│   ├── utils.py               # 工具函数
│   ├── routers/               # 接口层
│   │   ├── extract.py         # POST /api/v1/extract 单次请求/响应
│   │   ├── health.py          # GET /health + /ready 探活/就绪检查
│   │   └── render.py          # POST /api/v1/render 重新渲染
│   └── services/              # 业务层
│       ├── pipeline.py        # 提取管道编排（提取→地理编码→GeoJSON）
│       ├── geo.py             # 地理计算（朝代年份映射）
│       └── geojson.py         # GeoJSON FeatureCollection 构建
├── static/
│   ├── index.html             # 前端 SPA (MapLibre GL 地图 + 编辑面板)
│   ├── debug-terrain.html     # 地形调试页面
│   ├── css/map.css            # 地图样式
│   ├── js/
│   │   ├── app.js             # 应用逻辑（面板交互、编辑）
│   │   ├── map.js             # 地图渲染核心（MapLibre GL JS + Canvas 三层）
│   │   └── utils.js           # 纯函数工具
│   └── assets/icons/          # SVG 图标（旗帜、城门、山川等）
├── scripts/
│   ├── build_chgis.py         # CHGIS v6 数据管线构建
│   ├── code_review.py         # 代码审查脚本（DeepSeek-reasoner）
│   ├── vision.py              # Qwen-VL 视觉审查
│   ├── automate_review.py     # Playwright 自动化视觉审查
│   ├── describe.py            # 图片分析 (Qwen-VL)
│   ├── full_audit.py          # 全量审计
│   └── selftest.py            # 自测脚本
├── openspec/                  # OpenSpec 规范与变更工件
│   ├── specs/                 # 主规范文件
│   ├── changes/               # 变更归档
│   └── project.md             # 项目上下文
├── mcp_server/                # MCP 工具服务（Qwen 模型桥接）
├── data/
│   └── chgis_v6/
│       └── chgis_v6_points.csv
├── .github/workflows/         # CI 门禁
│   └── test.yml
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
| POST | `/api/v1/extract` | 提交历史文本，一次性返回地理实体提取 + 古地名匹配 + 地图数据 |
| POST | `/api/v1/render` | 提交编辑后的数据，重新地理编码和渲染 |
| GET | `/health` | 探活检查（k8s liveness probe） |
| GET | `/ready` | 就绪检查（k8s readiness probe） |
| GET | `/api/v1/config` | 获取前端配置（MapTiler API Key） |
| GET | `/` | 静态前端界面 |

### POST /api/v1/extract

```
Content-Type: application/json
Body: { "text": "岳飞率军自襄阳出发...", "dynasty": "南宋" }

Response: application/json
{
  "extract_id": "a1b2c3d4e5f6",
  "event_name": "岳飞北伐",
  "dynasty": "南宋",
  "places": [{"name": "襄阳", "context": "..."}],
  "boundaries": [{"name": "宋金边界", "description": "..."}],
  "person_places": [{"person": "岳飞", "place": "襄阳", "relation": "驻扎"}],
  "features": [{"name": "襄阳", "lng": 112.14, "lat": 32.01, "source": "chgis", ...}],
  "geojson": {"type": "FeatureCollection", "features": [...]},
  "scale": "battle",
  "elapsed": {"extract_ms": 1200, "geocode_ms": 300, "render_ms": 50, "total_ms": 1550}
}
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
