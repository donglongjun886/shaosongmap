## Context

上轮优化（图片预处理 1600px + PaddleOCR 960px 检测限 + batch 8 识别）将 OCR 从 ~10s 降至 ~3-4s。本轮在现有基础上继续微调参数并解决冷启动问题，同时将优化范围扩展到 DeepSeek API 侧。

## Goals / Non-Goals

**Goals:**
- 消除首次请求的 PaddleOCR 模型加载延迟（~2-3s）
- OCR 阶段再减少 0.5-1s
- DeepSeek API 响应时间减少 1-2s（通过 Prompt 精简）

**Non-Goals:**
- 不更换 OCR 引擎或 DeepSeek 模型
- 不引入本地 LLM
- 不改变 API 接口

## Decisions

### 决策1：启动时预加载 PaddleOCR

**选择**：在 `app.py` 启动事件中调用 `_get_ocr()` 触发模型加载。

**理由**：PaddleOCR 首次调用需下载/加载检测+识别模型到内存，耗时 2-3s。在 FastAPI startup 事件中预热，用户第一个请求不再受冷启动影响。

### 决策2：检测分辨率 960→720

**选择**：`text_det_limit_side_len=720`

**理由**：加上应用层 1600px 预处理，文字区域的实际分辨率仍在 100px 以上（1600px 截图中一行文字约 50-80px 高）。720px 检测限对阅读 App 截图足够，可减少约 25% 检测像素量。

### 决策3：灰度转换

**选择**：`image.convert("L")` 替代 `"RGB"`

**理由**：OCR 不依赖颜色信息。单通道数组只有 RGB 的 1/3 内存，检测和后续 numpy 操作都更快。对黑底白字/白底黑字的阅读 App 截图无任何影响。

### 决策4：Prompt 精简策略

**选择**：移除 JSON schema 中的注释行，合并相似规则，去掉示例。

当前两个 Prompt 都包含完整 JSON 示例。精简后：
- `_SYSTEM_PROMPT`：约 900 字符 → 约 500 字符
- `_TIMELINE_SYSTEM_PROMPT`：约 1400 字符 → 约 700 字符

每次 API 调用减少约 1000 tokens 输入，预计减少 1-2s 网络+推理延迟。
