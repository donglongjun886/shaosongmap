## Why

上轮优化将单章截图处理耗时从 14.8s 降至 ~7s（OCR 3-4s + DeepSeek 提取 3-4s）。OCR 端通过调整 PaddleOCR 参数仍可再挤 0.5-1s，DeepSeek API 端通过精简 Prompt 可减少 token 消耗降低网络延迟 1-2s。同时首次请求的模型冷启动问题尚未解决。

## What Changes

- PaddleOCR 模型启动时预加载，消除首次请求冷启动延迟
- 检测分辨率从 960px 降至 720px，进一步提高检测速度
- 检测阈值从 0.3 提至 0.4，减少噪声文本框
- 图片转灰度后再 OCR，减少颜色通道计算量
- 精简 `extractor.py` 两个 System Prompt，减少 JSON schema 注释和冗余规则描述，降低 DeepSeek API token 消耗

## Capabilities

### New Capabilities
<!-- None -->

### Modified Capabilities
- `screenshot-ocr`: PaddleOCR 初始化参数调整（720px、0.4阈值、灰度转换）、模型启动预加载
- `campaign-text-extraction`: System Prompt 精简优化

## Impact

- `shaosongmap/ocr.py`：`_init_ocr` 参数调整 + 新增启动预加载 + `recognize` 灰度转换
- `shaosongmap/extractor.py`：精简 `_SYSTEM_PROMPT` 和 `_TIMELINE_SYSTEM_PROMPT`
- `app.py`：启动时调用 OCR 预加载