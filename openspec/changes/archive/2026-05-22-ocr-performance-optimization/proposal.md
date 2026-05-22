## Why

用户反馈单章截图OCR识别+文本提取管道总耗时14.8秒，其中OCR阶段（PaddleOCR CPU推理）是主要瓶颈。需要在不降低识别准确率的前提下，通过图片预处理和PaddleOCR参数调优加速OCR，同时在管道各阶段增加耗时日志便于定位性能问题。

## What Changes

- OCR识别前新增图片预处理：长边超过1600px的截图自动缩放，减少像素量60%+
- PaddleOCR初始化增加检测限制、批量识别等加速参数
- 管道各阶段和OCR端点增加耗时日志（服务端logging + SSE事件`elapsed_ms`字段 + 最终result事件`elapsed`对象）
- OcrResponse模型新增`elapsed_ms`字段

## Capabilities

### New Capabilities
<!-- None -->

### Modified Capabilities
- `screenshot-ocr`: OCR识别新增图片预处理缩放步骤，PaddleOCR初始化参数调优
- `extraction-progress-streaming`: SSE进度事件新增`elapsed_ms`字段，result事件新增`elapsed`耗时分解对象

## Impact

- `shaosongmap/ocr.py`：新增`_preprocess_image()` + PaddleOCR参数调整
- `app.py`：新增`import time, logging`，管道/OCR端点耗时日志，SSE事件字段扩展，OcrResponse新增字段