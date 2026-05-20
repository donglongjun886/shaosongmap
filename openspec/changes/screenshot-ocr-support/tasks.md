## 1. 依赖安装与配置

- [x] 1.1 更新 `requirements.txt`：添加 `paddlepaddle` 和 `paddleocr`
- [x] 1.2 验证 PaddleOCR 安装成功，运行一次示例识别

## 2. OCR 模块（截图识别）

- [x] 2.1 编写 `shaosongmap/ocr.py`：封装 PaddleOCR 初始化，实现 `recognize(image_bytes)` 函数
- [x] 2.2 实现文本清洗函数 `clean_text(raw_lines)`：移除短行、UI 关键词过滤、段落合并
- [x] 2.3 实现 `ocr_main(image_bytes)` 主函数：识别 → 清洗 → 返回文本（不足 50 字则抛异常）

## 3. API 端点

- [x] 3.1 在 `app.py` 新增 `POST /api/ocr` 端点：接收图片上传，调用 OCR 模块，返回清洗后文本
- [x] 3.2 添加上传校验：文件类型检查（PNG/JPEG）、大小限制（10MB）

## 4. 前端截图上传

- [x] 4.1 在 `static/index.html` 的 textarea 上方添加截图上传区域（虚线框 + 拖拽/点击上传）
- [x] 4.2 实现前端图片预处理：上传前缩放（最长边 ≤ 1920px）
- [x] 4.3 实现上传逻辑：POST /api/ocr → 文本自动填入 textarea → 用户可校对后点击「生成地图」
- [x] 4.4 实现 Ctrl+V 粘贴截图支持

## 5. 测试

- [x] 5.1 编写 `tests/test_ocr.py`：测试清洗逻辑（正常文本、含 UI 噪声、文本不足 50 字）
- [x] 5.2 编写 `tests/test_api_ocr.py`：测试 `/api/ocr` 端点（正常上传、格式错误、文件过大）

## 6. 端到端验证

- [x] 6.1 准备一张《绍宋》起点 App 截图，手动测试完整链路（截图 → OCR → 地图）
- [x] 6.2 验收 spec 中所有 Scenario 通过