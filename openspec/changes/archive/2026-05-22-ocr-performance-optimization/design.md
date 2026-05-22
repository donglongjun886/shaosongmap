## Context

用户反馈单章截图 OCR + 提取管道总耗时 14.8 秒。分析发现 PaddleOCR 在 CPU 上对高清截图做全分辨率检测是主要瓶颈。此外缺少分阶段耗时数据，难以定位慢在哪个环节。

## Goals / Non-Goals

**Goals:**
- OCR 阶段耗时从 ~10秒 降至 2-4秒
- 管道各阶段耗时可视化（SSE + 服务端日志）

**Non-Goals:**
- 不引入 GPU 加速（用户环境限制）
- 不更换 OCR 引擎
- 不改变 API 接口签名（仅追加字段）

## Decisions

### 决策1：双重缩放的 OCR 加速策略

**选择**：应用层预处理缩放（长边1600px）+ PaddleOCR 内部检测限制（960px）双保险。

**理由**：
- 应用层先缩到 1600px，大幅减少像素量（iPhone截图从300万→120万像素，减60%）
- PaddleOCR 的 `text_det_limit_side_len=960` 保证检测阶段分辨率不会超过 960px
- 阅读 App 截图文字大而清晰，降到 960px 仍能准确识别，实测无影响
- 两层缩放互补：应用层控制输入，PaddleOCR 参数兜底

**替代方案**：
- ❌ 仅设 `text_det_limit_side_len=960`：PaddleOCR 的缩放实现可能不如 PIL LANCZOS 质量好
- ❌ 设更低阈值（480px）：小型中文文字可能识别失败

### 决策2：批量识别参数

**选择**：`text_recognition_batch_size=8`

**理由**：PaddleOCR 检测出文本框后逐张识别，设置 batch=8 可并行识别 8 个文本行。一页截图通常有 30-50 行文字，批量处理能减少推理轮次。

### 决策3：耗时精度

**选择**：使用 `time.perf_counter()`（毫秒级），SSE 事件以 `elapsed_ms` (int) 传输。

**理由**：`perf_counter()` 不受系统时钟调整影响，适合测耗时；毫秒精度足够诊断性能，避免浮点噪声。
