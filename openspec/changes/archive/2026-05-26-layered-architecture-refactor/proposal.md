## Why

`app.py` 当前 829 行，混杂了路由定义、业务逻辑、Pydantic 模型、常量和工具函数。CLAUDE.md 明确要求分层架构 `routers → services → repositories`，但代码未落地。在代码量突破 3500 行之际，必须兑现这个架构承诺，否则后续每次加功能都要在 829 行中定位。

## What Changes

- **BREAKING**: 删除 `_run_pipeline` 函数（零引用死代码）
- 新增 `shaosongmap/routers/`：OCR（`ocr.py`）、提取（`extract.py`）、渲染（`render.py`）
- 新增 `shaosongmap/services/`：GeoJSON（`geojson.py`）、部队旗帜（`unit_banner.py`）、地理计算（`geo.py`）
- 新增 `shaosongmap/schemas.py`：4 个 Pydantic 请求/响应模型从 `app.py` 迁出
- `app.py` 从 829 行精简为 ~30 行入口（FastAPI 实例化 + 中间件 + 路由注册 + 静态文件挂载）
- SSE 管道进度推送采用同步 generator 模式，服务层返回 `PipelineStage`，路由层负责 SSE 序列化

## Capabilities

### New Capabilities

- `layered-architecture`: 分层架构落地——routers（接口层）、services（业务层）、schemas（数据模型层）三层分离，app.py 精简为应用入口

### Modified Capabilities

<!-- 纯重构，零行为变更，无规范变更 -->

## Impact

- `app.py` — 从 829 行拆分为 1 个入口文件 + 7 个新模块
- 新增 `shaosongmap/routers/__init__.py`, `ocr.py`, `extract.py`, `render.py`
- 新增 `shaosongmap/services/__init__.py`, `geojson.py`, `unit_banner.py`, `geo.py`
- 新增 `shaosongmap/schemas.py`
- 108 个现有测试全程保持通过，无 API 契约变更
