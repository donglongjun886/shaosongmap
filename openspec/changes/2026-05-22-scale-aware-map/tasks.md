## 1. 数据模型

- [x] 1.1 新增 `MilitaryScale = Literal["tactical", "battle", "strategic"]`
- [x] 1.2 `CampaignExtract` 新增可选 `scale` 字段（default=None）

## 2. LLM Prompt

- [x] 2.1 `_SYSTEM_PROMPT` JSON 模板新增 `"scale": "tactical|battle|strategic|null"` + 分类规则
- [x] 2.2 `_TIMELINE_SYSTEM_PROMPT` 同步新增

## 3. API 管道

- [x] 3.1 `ExtractResponse` 新增 `scale` 字段
- [x] 3.2 `RenderRequest` 新增 `scale` 字段
- [x] 3.3 `_run_pipeline()` 返回注入 scale
- [x] 3.4 SSE result dict 注入 scale
- [x] 3.5 `render_modified()` 重建 CampaignExtract 和返回 ExtractResponse 时传递 scale

## 4. 前端

- [x] 4.1 `updateMap()` 根据 data.scale 查表设置 maxZoom
- [x] 4.2 `collectModifiedData()` 回传 scale
- [x] 4.3 结果面板显示尺度标签

## 5. 测试

- [x] 5.1 `test_extract_full_fields` 新增 scale 断言
- [x] 5.2 新增 `test_extract_scale_tactical`
- [x] 5.3 新增 `test_extract_scale_strategic`
- [x] 5.4 新增 `test_extract_scale_invalid`
- [x] 5.5 `test_extract_timeline_full_sequence` 新增 scale 断言
- [x] 5.6 全量 82 测试通过
