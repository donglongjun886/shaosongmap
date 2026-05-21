## ADDED Requirements

### Requirement: 批量OCR接口

系统 SHALL 提供 `POST /api/ocr/batch` 接口，接收多张截图（multipart/form-data，字段名 `files`），依次执行OCR识别、文本去重、拼接后返回完整文本。

该接口 MUST：
- 支持同时上传 2-10 张 PNG/JPEG 截图
- 对每张截图独立调用现有的 `ocr_main()` 进行OCR和清洗
- 在相邻图的清洗后文本之间执行前后缀去重拼接
- 通过 SSE (`text/event-stream`) 返回处理进度
- 单张截图失败时立即中止并返回错误，指明失败图片的序号

#### Scenario: 批量上传3张截图

- **WHEN** 用户通过 POST /api/ocr/batch 上传 3 张连续章节截图
- **THEN** 系统依次OCR每张图，去重拼接后通过 SSE complete 事件返回完整文本

#### Scenario: 批量上传中某张图片格式错误

- **WHEN** 第 2 张图片为非 PNG/JPEG 格式
- **THEN** 系统返回 400 错误，提示「第 2 张截图格式不支持，仅支持 PNG 和 JPEG 格式」

#### Scenario: 批量上传中某张图片过大

- **WHEN** 第 1 张图片超过 10MB
- **THEN** 系统返回 413 错误，提示「第 1 张截图大小超过 10MB 限制」

### Requirement: 文本去重拼接函数

系统 SHALL 提供 `merge_texts(texts: list[str]) -> tuple[str, int]` 函数，对OCR清洗后的多段文本进行相邻去重拼接。

该函数 MUST：
- 对相邻文本段执行前后缀最长公共子串匹配
- 匹配窗口限定为 200 字符（前一段尾部 200 字符 vs 后一段头部 200 字符）
- 返回 (拼接后完整文本, 去除的重复字符总数)

#### Scenario: 两段文本有尾部/头部重叠

- **WHEN** text1 末尾包含 "孔明曰：此乃天赐良机也"，text2 开头包含 "此乃天赐良机也。玄德大喜"
- **THEN** merge_texts 识别出重叠 "此乃天赐良机也"，返回去重后的拼接文本

#### Scenario: 两段文本完全无重叠

- **WHEN** text1 和 text2 的首尾没有公共子串
- **THEN** merge_texts 直接拼接 text1 + text2，removed_dup 为 0