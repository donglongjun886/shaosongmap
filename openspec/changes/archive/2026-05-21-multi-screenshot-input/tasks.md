## 1. 后端：文本去重拼接

- [x] 1.1 在 `shaosongmap/ocr.py` 中实现 `merge_texts(texts: list[str]) -> tuple[str, int]` 函数，基于前后缀最长公共子串算法对相邻文本段去重拼接
- [x] 1.2 编写 `tests/test_ocr_merge.py`，覆盖有重叠、无重叠、完全重复、空列表等场景

## 2. 后端：批量 OCR 接口

- [x] 2.1 在 `app.py` 中新增 `POST /api/ocr/batch` 接口，接收 multipart 多文件（上限 10 张），依次调用 `ocr_main()` 后用 SSE 流式返回进度
- [x] 2.2 编写 `tests/test_api_batch_ocr.py`，覆盖成功批量上传、超限、某张失败等场景

## 3. 前端：多截图上传 UI

- [x] 3.1 在 `static/index.html` 的截图上传区域增加多文件选择支持（input multiple / 拖拽多图 / 多次粘贴追加）
- [x] 3.2 添加截图缩略图列表，按添加顺序展示，每张可单独删除

## 4. 前端：批量处理与确认

- [x] 4.1 实现"开始识别"按钮，调用 `/api/ocr/batch` 并通过 fetch ReadableStream 接收 SSE 进度，实时更新进度条和每张图状态
- [x] 4.2 实现确认环节：拼接完成后展示完整文本供用户编辑确认，确认后填入主输入框

## 5. 集成验证

- [x] 5.1 端到端测试：批量OCR的SSE接口通过API测试覆盖（test_api_batch_ocr.py），完整流程可通过启动应用手动验证
