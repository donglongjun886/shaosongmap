## MODIFIED Requirements

### Requirement: 代码分层组织

系统 SHALL 按 `routers → services → schemas` 三层架构组织代码，`app.py` 精简为应用入口。

**routers/ 层（接口层）：**
- SHALL 仅包含 FastAPI 路由定义和 SSE 序列化逻辑
- MUST 不包含业务逻辑和管道编排逻辑
- 每个路由文件 SHALL 对应一个 API 领域：`ocr.py`、`extract.py`、`render.py`

**services/ 层（业务层）：**
- SHALL 包含所有业务逻辑函数，与 HTTP/SSE 传输格式无关
- SHALL 包含提取管道编排函数（`run_extract_pipeline`），以同步 generator 函数实现
- 文件 SHALL 按领域概念分组：`pipeline.py`（提取管道编排）、`geojson.py`（地图要素→GeoJSON）、`unit_banner.py`（部队→旗帜标记）、`geo.py`（地理计算）

**schemas 层（数据模型层）：**
- SHALL 包含所有 Pydantic 请求/响应模型
- MUST 使用 `shaosongmap/schemas.py` 单文件

#### Scenario: 新增 API 端点

- **WHEN** 开发者需要新增一个 API 端点
- **THEN** 在对应领域路由文件中添加路由函数，业务逻辑委托给 services 层，无需在单体文件中定位

#### Scenario: 测试服务层函数

- **WHEN** 开发者编写业务逻辑单元测试
- **THEN** 可以直接 `from shaosongmap.services.pipeline import run_extract_pipeline` 测试，无需启动 FastAPI 应用

#### Scenario: 管道逻辑独立于传输层

- **WHEN** 未来需要将相同的管道逻辑改为 WebSocket 推送
- **THEN** 仅需修改路由层序列化方式，服务层 `run_extract_pipeline` 无需变更
