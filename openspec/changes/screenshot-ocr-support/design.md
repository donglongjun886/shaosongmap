## Context

MVP 已实现「粘贴文本 → 生成地图」的核心链路。起点等网文平台限制文本复制，需要新增截图 OCR 输入方式。现有 Extractor / Geocoder 管道不变，仅在输入端增加 OCR 前置处理。

## Goals / Non-Goals

**Goals:**
- 新增 `screenshot-ocr` 模块：PaddleOCR 识别 + 文本清洗
- 新增 `POST /api/ocr` 端点：接收截图，返回清洗后的文本
- 前端新增截图上传区域（拖拽/粘贴），与 textarea 并存
- OCR 管道与 Extractor 管道解耦：OCR 端点独立返回文本，前端再调用 `/api/extract`

**Non-Goals:**
- 不做 OCR 拼写纠错（V2）
- 不做竖排文本专项优化
- 不换 LLM、不改现有管道
- 不自动识别截图中是否包含战役内容

## Decisions

### 1. OCR 引擎：PaddleOCR

- **决定**: 使用 PaddleOCR（`paddleocr` 包），CPU 模式运行
- **理由**: 中文识别率 97%+，Python 原生集成，与 FastAPI 进程内调用
- **备选方案**: Tesseract（中文弱）、云端 OCR API（延迟高、成本高）

### 2. 管道分离：OCR 和 Extract 是两个独立端点

```
  POST /api/ocr        POST /api/extract
  (截图→文本)           (文本→地图)

  前端负责串联：OCR → 拿到文本 → 填入 textarea → 调用 extract
```

- **决定**: `/api/ocr` 和 `/api/extract` 独立，OCR 只返回文本，不自动触发提取
- **理由**: 用户可能在 OCR 后校对文本再提交；两个端点职责单一，便于测试和复用
- **备选方案**: 一个 `/api/extract-from-image` 端点 OCR+Extract 串行 → 否决，用户无法校对

### 3. 文本清洗策略

起点截图噪声来源：
- App 顶部状态栏（时间、电量）
- 底部导航栏（「上一章」「下一章」「目录」）
- 章节标题行（如「第三百一十二章 北伐」）
- 段落间多余空行

- **决定**: 用规则做基础清洗——移除短行（<6字）、去除非中文字符行、合并断行、移除已知 UI 关键词（「上一章」「下一章」「目录」「书架」等）
- **理由**: 规则覆盖 80% 噪声场景，实现成本低；LLM 清洗会增加延迟和成本

### 4. 前端交互：拖拽 + 粘贴截图

- **决定**: 在 textarea 上方添加截图区，支持拖拽图片和 Ctrl+V 粘贴截图，OCR 完成后自动填入 textarea，用户可校对后提交
- **理由**: 最小化前端改动，保持现有 textarea 提交流程不动

### 5. 图片大小处理

- **决定**: 前端上传前缩放图片（最长边 ≤ 1920px），后端不再做额外压缩
- **理由**: 移动端截图通常 1080×2400，缩放后 OCR 精度不受影响，传输和识别更快

## Risks / Trade-offs

- **[PaddleOCR 安装体积大]** → PaddlePaddle CPU 包约 400MB，首次安装耗时；通过 `requirements.txt` 明确说明，部署时预装
- **[OCR 错误传播到 Geocoder]** → 地名识别错误（如「汴京→沐京」）会导致匹配失败；通过 CHGIS 模糊匹配和 LLM 推断兜底缓解，不做专项纠错
- **[截图包含非正文内容]** → 清洗规则可能误删有效内容（如极短的地名行）；清洗后保留至少 50 字符才允许提交
- **[多栏/竖排文字]** → PaddleOCR 默认行识别，竖排或分栏可能输出错乱；V1 不做专项处理，已知限制

## Open Questions

- PaddleOCR 模型首次加载需下载（~100MB），是否需预下载到 Docker 镜像中？（当前无 Docker，暂不涉及）
