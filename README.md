# 绍宋地图 (ShaosongMap)

> 让历史小说读者「边读边看地图」—— 输入战役段落，生成古代地图。

针对《绍宋》等宋代历史小说读者，从截图或文本中自动提取战役地名、将领、行军路线，匹配宋代古地名坐标，渲染为交互式地图。

## 功能特性

- **📷 截图 OCR** — 上传起点 App 截图，PaddleOCR 自动识别文字（过滤 UI 噪音）
- **🏗️ 战役信息提取** — DeepSeek LLM 提取阵营、将领、地名、行军路线等结构化数据
- **🗺️ 古地名匹配** — 基于 CHGIS v6 的 934 条宋代地名数据，精确匹配经纬度坐标
- **🧠 LLM 推断兜底** — 虚构地名或极小地点交由 LLM 根据上下文推断近似坐标
- **🌏 交互式地图** — Leaflet 地图展示古地名坐标和行军路线，可区分数据来源
- **✏️ 结果可编辑** — 提取结果面板支持增删改查，修改后可重新渲染地图
- **📡 SSE 进度推送** — 提取→匹配→渲染三阶段进度实时展示

## 技术栈

| 层级 | 技术 |
|------|------|
| Web 框架 | FastAPI + Pydantic |
| OCR | PaddleOCR 3.x |
| LLM | DeepSeek API (OpenAI 兼容) |
| 古地名数据 | CHGIS v6 (Harvard Dataverse) |
| 前端 | 原生 HTML/CSS/JS + Leaflet |
| 测试 | pytest (40 个测试用例) |

## 快速开始

### 环境要求

- Python 3.10+
- pip

### 安装

```bash
git clone https://github.com/donglongjun886/shaosongmap.git
cd shaosongmap
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 配置

创建 `.env` 文件，设置 DeepSeek API Key：

```bash
cp .env.example .env   # 如果有示例文件
# 编辑 .env，填入：
# DEEPSEEK_API_KEY=your_key_here
# DEEPSEEK_BASE_URL=https://api.deepseek.com
```

> 如果没有 `.env.example`，手动创建 `.env` 文件，参考上述变量。

### 启动

```bash
python -m uvicorn app:app --host 0.0.0.0 --port 8765 --reload
```

浏览器打开 http://localhost:8765

## 项目结构

```
shaosongmap/
├── app.py                  # FastAPI 应用入口，API 端点定义
├── requirements.txt        # Python 依赖
├── shaosongmap/
│   ├── extractor.py        # DeepSeek LLM 战役文本提取
│   ├── geocoder.py         # CHGIS 精确匹配 + LLM 推断兜底
│   ├── models.py           # Pydantic 数据模型
│   └── ocr.py              # PaddleOCR 截图识别与文本清洗
├── static/
│   └── index.html          # 前端 SPA (Leaflet 地图 + 结果面板)
├── scripts/
│   └── build_chgis.py      # CHGIS v6 数据下载与预处理脚本
├── data/
│   └── chgis_v6/
│       └── chgis_v6_points.csv  # 934 条宋代地名数据
└── tests/
    ├── test_api.py          # API 端点测试 (SSE)
    ├── test_api_ocr.py      # OCR 端点测试
    ├── test_api_render.py   # Render 端点测试
    ├── test_api_sse.py      # SSE 事件格式测试
    ├── test_extractor.py    # 提取器测试 (含对话/军事混合场景)
    ├── test_geocoder.py     # 地名匹配测试
    └── test_ocr.py          # OCR 清洗逻辑测试
```

## API 概览

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/ocr` | 上传截图 (PNG/JPEG)，返回 OCR 识别文本 |
| POST | `/api/extract` | 提交战役文本，SSE 流式返回提取+匹配+地图数据 |
| POST | `/api/render` | 提交编辑后的数据，重新地理编码和渲染 |
| GET | `/` | 静态前端界面 |

### POST /api/ocr

```
Content-Type: multipart/form-data
Body: file (PNG/JPEG, max 10MB)

Response: { "text": "...", "raw_lines": 23 }
```

### POST /api/extract

```
Content-Type: application/json
Body: { "text": "岳飞率军自襄阳出发...", "dynasty": "南宋" }

Response: text/event-stream (SSE)
  event: progress → { "stage": "extract_done" }
  event: progress → { "stage": "geocode_done", "detail": "匹配古地名 (8 CHGIS + 2 LLM推断)" }
  event: progress → { "stage": "render_done" }
  event: result   → { "features": [...], "routes": [...], "geojson": {...} }
```

### POST /api/render

```
Content-Type: application/json
Body: { "places": [...], "routes": [...], "factions": [...], "dynasty": "宋" }

Response: { "features": [...], "routes": [...], "geojson": {...} }
```

## 开发

```bash
# 运行测试
pytest tests/ -v

# 运行特定测试
pytest tests/ -k "geocode" -v

# 重新生成 CHGIS 数据（需要网络）
python scripts/build_chgis.py
```

## 许可

本项目采用**双重许可**：

| 范围 | 许可 | 说明 |
|------|------|------|
| 代码（`shaosongmap/`、`app.py`、`static/`、`scripts/`、`tests/`） | [MIT License](LICENSE) | 可自由使用、修改、分发，仅需保留版权声明 |
| 数据（`data/chgis_v6/chgis_v6_points.csv`） | [CHGIS v6 学术许可](https://dataverse.harvard.edu/dataverse/chgis_v6) | 免费用于学术和个人用途；商业使用需联系 Harvard Fairbank Center for Chinese Studies |

CHGIS v6 数据版权归 &copy; Fairbank Center for Chinese Studies, Harvard University 所有。`data/chgis_v6/chgis_v6_points.csv` 是从 CHGIS v6 原始数据筛选衍生的子集，遵循原始数据的许可条款。