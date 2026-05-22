## 1. OCR 加速

- [x] 1.1 实现 `_preprocess_image()` 函数：长边超 1600px 缩放至 1600px，LANCZOS 重采样
- [x] 1.2 `_init_ocr()` 新增 PaddleOCR 加速参数（`text_det_limit_side_len=960`、`text_recognition_batch_size=8` 等）
- [x] 1.3 `recognize()` 调用 `_preprocess_image()` 预处理后再 OCR

## 2. 耗时日志

- [x] 2.1 `app.py` 导入 `time`、`logging`，添加 logger 实例
- [x] 2.2 `/api/ocr` 端点：OCR 调用前后计时，logging 输出 + OcrResponse 新增 `elapsed_ms`
- [x] 2.3 `/api/ocr/batch` 端点：每张 OCR、去重拼接、总耗时计时，SSE 事件追加 `elapsed_ms`
- [x] 2.4 `/api/extract` 管道：三阶段分别计时，SSE progress 事件追加 `elapsed_ms`，result 事件追加 `elapsed` 对象
- [x] 2.5 管道全部完成时 logging 输出汇总耗时（各阶段 + 总计）