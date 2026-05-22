## 1. OCR 参数调优

- [x] 1.1 `_init_ocr()`：`text_det_limit_side_len` 从 960 降至 720，`text_det_thresh` 从 0.3 提至 0.4
- [x] 1.2 `recognize()`：`image.convert("RGB")` 改为 `"L"` 灰度转换
- [x] 1.3 `app.py`：FastAPI startup 事件中调用 `_get_ocr()` 预加载模型

## 2. Prompt 精简

- [x] 2.1 精简 `_SYSTEM_PROMPT`：移除 JSON schema 注释行，合并冗余规则，去掉示例数据
- [x] 2.2 精简 `_TIMELINE_SYSTEM_PROMPT`：同上，保留核心指令语义不变

## 3. 测试

- [x] 3.1 运行全量测试确认无回归