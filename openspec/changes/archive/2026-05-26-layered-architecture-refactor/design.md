## Context

`app.py` 当前 829 行，包含路由定义（4 个端点）、Pydantic 模型（4 个类）、服务函数（10 个）、常量和工具函数。CLAUDE.md 要求分层架构 `routers → services → repositories`，但代码未落地。项目处于快速增长期（近期日提交 6 次，~2300 行变更），模块化是后续所有工作的前提。

## Goals / Non-Goals

**Goals:**
- 将 `app.py` 从 829 行精简为 ~30 行（FastAPI 入口 + 中间件 + 路由注册 + 静态文件）
- 建立 `routers/`（接口层）、`services/`（业务层）、`schemas.py`（数据模型层）三层结构
- SSE 管道逻辑与传输格式解耦：服务层返回数据，路由层负责 SSE 序列化
- 删除死代码 `_run_pipeline`

**Non-Goals:**
- 不创建 `repositories/` 层（暂无数据库，留到引入 PostgreSQL 时再做）
- 不修改任何 API 契约、函数签名、业务行为
- 不新增或修改测试
- 不拆分前端 `static/index.html`

## Decisions

### 1. 目录位置：`shaosongmap/` 包内

**选择**：`shaosongmap/routers/`、`shaosongmap/services/`  
**替代方案**：根级 `app/routers/`、`app/services/`

理由：路由和服务是应用架构层，但与 `shaosongmap` 核心包紧密耦合（所有导入都从 `shaosongmap.` 开始），放在包内保持导入路径自然（`from shaosongmap.services.geojson import ...`），避免顶级目录膨胀。

### 2. 删除 `_run_pipeline`

`_run_pipeline` 在代码库中零引用——无路由、脚本、测试调用。拆分重构是最佳清理时机，带着死代码迁移到新模块会污染 `git blame`。以后需要统一管道时再抽象。

### 3. 服务层粗粒度（3 文件）

**选择**：`geojson.py`、`unit_banner.py`、`geo.py`  
**替代方案**：7 个细粒度文件

每个文件 50-210 行，边界按领域概念对齐（地图要素、部队旗帜、地理计算）。细粒度会导致一半文件不足 30 行，增加跳转成本而无实际收益。后续文件超过 ~300 行或出现明显子领域时再拆。

### 4. SSE 拆分：服务返回 PipelineStage，路由做 SSE

**选择**：服务函数用同步 generator yield `PipelineStage` 对象，路由层遍历并转为 SSE 字符串  
**替代方案**：服务层直接 yield SSE 字符串（async generator）

理由：分层架构核心原则——传输格式是路由的事。解耦后：
- 服务层函数可独立测试（不依赖 FastAPI/SSE）
- 以后换 WebSocket 或 REST 同步时只改路由层
- 进度推送完整保留

### 5. Schemas 单文件

**选择**：`shaosongmap/schemas.py`（4 个类，~50 行）  
**替代方案**：`schemas/requests.py` + `schemas/responses.py`

当前仅 4 个 Pydantic 类共 46 行，单文件足够。拆分子目录属于过度设计。

## Risks / Trade-offs

- **[风险] 导入路径变更** → `app.py` 中 `from app import app` 的测试导入可能受影响。确认测试使用 `from app import app`（非包内导入），拆分后导入路径不变
- **[风险] 循环导入** → services 可能互相引用。按当前分析，3 个 service 文件之间无相互依赖，均可独立导入
- **[权衡] PipelineStage 新增定义** → 引入轻量 dataclass 作为服务-路由契约，增加 ~10 行代码，但换来清晰的分层边界
