## MODIFIED Requirements

### Requirement: 截图上传与 OCR 识别

系统 SHALL 接收 PNG/JPEG 格式的截图，通过 PaddleOCR 进行中文文字识别，返回识别后的纯文本。

OCR 识别前 SHALL 对图片进行预处理：若图片长边超过 1600px，则按比例缩放至长边 1600px，随后转换为灰度图（单通道），减少计算量。

PaddleOCR 初始化 SHALL 使用以下加速参数：
- `text_det_limit_side_len=720`，`text_det_limit_type="max"`：检测阶段限制长边不超过 720px
- `text_det_thresh=0.4`：检测阈值，减少噪声区域误检
- `text_det_box_thresh=0.5`
- `text_recognition_batch_size=8`：批量并行识别 8 个文本行

系统 SHALL 在 FastAPI 应用启动时预加载 PaddleOCR 模型，避免首次请求的冷启动延迟。

#### Scenario: 成功识别截图文字

- **WHEN** 用户上传一张包含中文战役文本的截图
- **THEN** 系统返回识别后的文本字符串，每个文本块包含坐标和置信度

#### Scenario: 高清截图自动缩放

- **WHEN** 用户上传一张 1170×2532 像素的高清截图
- **THEN** 系统在 OCR 识别前将图片缩放至约 740×1600 像素并转为灰度，日志输出缩放比例

#### Scenario: 小图不缩放

- **WHEN** 用户上传一张长边不超过 1600px 的截图
- **THEN** 系统直接转为灰度后进行 OCR，不做预处理缩放

#### Scenario: 图片格式不支持

- **WHEN** 用户上传非 PNG/JPEG 格式的文件（如 GIF、WebP）
- **THEN** 系统返回 400 错误，提示「仅支持 PNG 和 JPEG 格式」

#### Scenario: 图片过大

- **WHEN** 用户上传超过 10MB 的图片
- **THEN** 系统返回 413 错误，提示「图片大小不能超过 10MB」
