## Why

当前系统支持战术/战役/战略三级地图、时间轴模式、部队标记、进攻箭头，架构复杂（MapLibre + 三层Canvas + roughjs + tacticalRenderer + SSE 分步管道）。但实际使用场景只需要一种静态战役地图——展示地名和行军路线即可。大幅简化前后端，降低维护成本。

## What Changes

- 删除时间轴模式、部队标记、进攻箭头、scale 分级
- 删除三层 Canvas 渲染层（canvasRenderer/terrainRenderer）+ tacticalRenderer + roughjs
- 后端 LLM 提示词简化（去掉 events/unit_states/direction/scale 规则）
- 删除 `unit_banner.py`、`extract_timeline()`、相关数据模型
- SSE 流式保留但简化（仅推送进度，最终返回单一结果）
- API 请求体删除 `mode` 字段

## Capabilities

### New Capabilities
- `simplify-static-map`: 单一静态战役地图渲染，仅展示地名标记和行军路线

### Modified Capabilities
- `campaign-map-rendering`: 删除时间轴、部队、箭头相关渲染能力
- `campaign-text-extraction`: 简化 LLM 提示词，删除 events/unit_states/direction/scale 提取规则

## Impact

- 删除文件：tacticalRenderer.js, canvasRenderer.js, terrainRenderer.js, debug-terrain.html, debug-styles.html, unit_banner.py
- 修改文件：extractor.py, pipeline.py, models.py, services/geo.py, routers/extract.py, schemas.py, app.js, index.html, map.js, utils.js
- 删除依赖：roughjs CDN
- 净删代码：约 2000 行前端 + 约 500 行后端
