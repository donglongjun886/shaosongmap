## 1. SSE 分阶段进度推送（后端）

- [x] 1.1 修改 `app.py` 的 `/api/extract` 端点，改为 SSE 流式响应（`text/event-stream`）
- [x] 1.2 实现管道编排函数：在每个阶段完成后 yield 一个 `progress` 事件（extract_done / geocode_done / render_done）
- [x] 1.3 实现错误处理：任意阶段失败时 yield `error` 事件并中断流
- [x] 1.4 添加 SSE 响应头：`X-Accel-Buffering: no`、`Cache-Control: no-cache`

## 2. `/api/render` 重新渲染端点

- [x] 2.1 在 `app.py` 新增 `POST /api/render` 端点，接收修正后的 CampaignExtract 数据
- [x] 2.2 实现管道：数据校验 → geocode → GeoJSON（跳过 extract 阶段）
- [x] 2.3 添加请求体 Pydantic 模型校验

## 3. 增强 Extractor Prompt

- [x] 3.1 更新 `shaosongmap/extractor.py` 的 `_SYSTEM_PROMPT`，增加对混合内容（朝堂对话/议论）的识别和忽略指令
- [x] 3.2 新增规则：假设性军事建议（如「臣以为应从X出兵」）不被提取为实际行军节点
- [x] 3.3 新增规则：纯对话/描写文本无军事行动时返回空 places/routes

## 4. 前端：分阶段进度条

- [x] 4.1 在 `static/index.html` 中新增进度条 UI 组件（4 个阶段节点 + 连线 + 状态图标）
- [x] 4.2 实现 SSE 流读取，解析 `progress` / `result` / `error` 事件
- [x] 4.3 实现阶段状态更新：pending (○) → active (⏳) → done (✓) → error (✗)
- [x] 4.4 截图流程显示 4 阶段（含 OCR），文本流程显示 3 阶段（不含 OCR）

## 5. 前端：可编辑提取结果面板

- [x] 5.1 重构结果面板：地名列表改为可编辑 input 字段 + 删除按钮
- [x] 5.2 路线 from/to/via 改为可编辑字段
- [x] 5.3 将领列表改为可编辑 + 新增/删除
- [x] 5.4 添加「重新渲染」按钮，收集修改后数据调用 `/api/render`
- [x] 5.5 重新渲染后仅更新地图部分，不重跑进度条

## 6. 前端：键盘快捷键

- [x] 6.1 绑定 Ctrl+Enter（macOS Cmd+Enter）触发提交
- [x] 6.2 绑定 Esc 关闭地图 popup 和错误提示

## 7. 测试

- [x] 7.1 编写 `tests/test_api_render.py`：测试 `/api/render` 端点的正常流程和校验失败
- [x] 7.2 更新 `tests/test_extractor.py`：新增混合内容场景测试（朝堂对话 + 军事行动）
- [x] 7.3 编写 `tests/test_api_sse.py`：测试 SSE 端点的事件流格式

## 8. 端到端验证

- [x] 8.1 用测试文本手动验证分阶段进度条展示
- [x] 8.2 手动验证提取结果编辑 → 重新渲染 → 地图更新链路
- [x] 8.3 验收 spec 中所有 Scenario 通过
