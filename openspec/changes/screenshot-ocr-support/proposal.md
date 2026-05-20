## Why

起点等网文平台限制文本复制（可能出于版权保护），读者无法直接粘贴《绍宋》的战役段落。目前 MVP 只支持粘贴文本，对移动端读者尤其不友好。需要新增截图 OCR 功能，让读者截屏即可获得地图。

## What Changes

- 新增 `ocr.py` 模块：封装 PaddleOCR，接收截图返回识别文本
- 新增文本清洗逻辑：去除截图中的 App UI 噪声（按钮、状态栏等），合并为连续段落
- 新增 `POST /api/ocr` 端点：接收图片上传，返回清洗后的文本
- 修改前端页面：在 textarea 上方新增截图拖拽/粘贴区域，支持文本粘贴和截图上传两种输入方式
- 现有 Extractor / Geocoder / 地图渲染管道**不变**

## Capabilities

### New Capabilities

- `screenshot-ocr`: 接收截图图片（PNG/JPEG），通过 PaddleOCR 进行中文文字识别，清洗去除 UI 噪声后输出连续文本段落，供 Extractor 管道使用

### Modified Capabilities

- `campaign-map-rendering`: 输入方式从「仅支持粘贴文本」扩展为「支持粘贴文本 + 截图上传」，两种输入方式共存，用户可选择使用

## Impact

- **新增依赖**: `paddleocr`、PaddlePaddle（Python 包）
- **新增代码**: `shaosongmap/ocr.py`（OCR 识别 + 文本清洗）、`app.py` 新增 `/api/ocr` 端点
- **修改代码**: `static/index.html`（新增截图上传区域）、`app.py`（新增 upload 相关路由）
- **现有管道**: Extractor / Geocoder 不受影响
- **部署影响**: 需要安装 PaddlePaddle（CPU 版约 400MB）
