## Why

当前系统对所有军事文本使用相同的 maxZoom=10 渲染地图，不区分文本的军事尺度。用户输入的文本可能描述 1-10km 的局部战术冲突，也可能描述数百公里的跨省战略部署，一刀切的缩放导致小尺度地图空旷无聊、大尺度地图缺乏全局视野。

## What Changes

- `CampaignExtract` 模型新增可选 `scale` 字段（tactical / battle / strategic）
- 两个 LLM 提取 Prompt 新增 scale 分类规则，让 LLM 在提取阶段自动判断文本的军事层级
- API 管道全链路传递 scale：ExtractResponse / RenderRequest / _run_pipeline / SSE result / render_modified
- 前端 `updateMap()` 根据 scale 查表设置 maxZoom：tactical=14 / battle=10 / strategic=6
- 前端结果面板显示尺度标签

## Capabilities

### Modified Capabilities
- `campaign-text-extraction`: 新增 scale 字段，LLM 自动分类军事层级
- `campaign-map-rendering`: 前端根据 scale 调整地图缩放策略

## Impact

- `shaosongmap/models.py`：新增 MilitaryScale 字面量 + CampaignExtract.scale 字段
- `shaosongmap/extractor.py`：两个 System Prompt 新增 scale 输出和分类规则
- `app.py`：ExtractResponse / RenderRequest / _run_pipeline / SSE result / render_modified 五处传递 scale
- `static/index.html`：updateMap 查表 maxZoom + collectModifiedData 回传 + 尺度标签
- `tests/test_extractor.py`：新增 3 个 scale 测试 + 1 个断言
- `tests/test_timeline.py`：新增 scale 断言
