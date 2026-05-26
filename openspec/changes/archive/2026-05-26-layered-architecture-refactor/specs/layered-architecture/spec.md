## ADDED Requirements

### Requirement: 代码分层组织

系统 SHALL 按 `routers → services → schemas` 三层架构组织代码，`app.py` 精简为应用入口。

**routers/ 层（接口层）：**
- SHALL 仅包含 FastAPI 路由定义和 SSE 序列化逻辑
- MUST 不包含业务逻辑
- 每个路由文件 SHALL 对应一个 API 领域：`ocr.py`、`extract.py`、`render.py`

**services/ 层（业务层）：**
- SHALL 包含所有业务逻辑函数，与 HTTP/SSE 传输格式无关
- 文件 SHALL 按领域概念分组：`geojson.py`（地图要素→GeoJSON）、`unit_banner.py`（部队→旗帜标记）、`geo.py`（地理计算）

**schemas 层（数据模型层）：**
- SHALL 包含所有 Pydantic 请求/响应模型
- MUST 使用 `shaosongmap/schemas.py` 单文件

#### Scenario: 新增 API 端点

- **WHEN** 开发者需要新增一个 API 端点
- **THEN** 在对应领域路由文件中添加路由函数，业务逻辑委托给 services 层，无需在 829 行单体文件中定位

#### Scenario: 测试服务层函数

- **WHEN** 开发者编写业务逻辑单元测试
- **THEN** 可以直接 `from shaosongmap.services.geojson import _make_geojson` 测试，无需启动 FastAPI 应用

### Requirement: SSE 管道分层

系统 SHALL 在 `/api/extract` SSE 流式响应中实现传输与逻辑分离。

服务层 MUST：
- 以同步 generator 函数执行管道逻辑
- yield `PipelineStage` 对象（包含 `name` 和 `data` 字段）

路由层 MUST：
- 遍历 generator 产出的 `PipelineStage`
- 调用 `_sse_event()` 转为 SSE 格式字符串
- 返回 `StreamingResponse`

#### Scenario: 管道逻辑与传输解耦

- **WHEN** 未来需要将相同的管道逻辑改为 WebSocket 推送
- **THEN** 仅需修改路由层序列化方式，服务层代码无需变更

### Requirement: 零行为变更

本次重构 MUST 不修改任何 API 端点路径、请求/响应格式、函数签名或业务逻辑。所有 108 个现有测试 SHALL 在重构前后保持通过。

#### Scenario: 重构后测试全绿

- **WHEN** 分层架构重构完成
- **THEN** 运行 `pytest tests/ -v` 全部 108 个测试通过，无任何修改

### Requirement: 死代码清理

系统 SHALL 删除 `_run_pipeline` 函数（零引用死代码），不迁移到新模块。

#### Scenario: 确认清理

- **WHEN** 重构完成后运行 `grep -r "_run_pipeline" shaosongmap/ app.py`
- **THEN** 无任何匹配结果
