# Screenshot OCR 截图文字识别

## Purpose

支持用户上传起点等网文 App 的截图，通过 PaddleOCR 进行中文文字识别，清洗 UI 噪声后返回可供后续文本提取管道使用的连续文本。

## Requirements

### Requirement: 截图上传与 OCR 识别

系统 SHALL 接收 PNG/JPEG 格式的截图，通过 PaddleOCR 进行中文文字识别，返回识别后的纯文本。

#### Scenario: 成功识别截图文字

- **WHEN** 用户上传一张包含中文战役文本的截图
- **THEN** 系统返回识别后的文本字符串，每个文本块包含坐标和置信度

#### Scenario: 图片格式不支持

- **WHEN** 用户上传非 PNG/JPEG 格式的文件（如 GIF、WebP）
- **THEN** 系统返回 400 错误，提示「仅支持 PNG 和 JPEG 格式」

#### Scenario: 图片过大

- **WHEN** 用户上传超过 10MB 的图片
- **THEN** 系统返回 413 错误，提示「图片大小不能超过 10MB」

### Requirement: 文本清洗

系统 SHALL 对 OCR 原始输出进行清洗，去除 App UI 噪声后合并为连续段落文本。

清洗规则 MUST 包括：
- 移除长度小于 6 个中文字符的文本行
- 移除已知 UI 关键词行（「上一章」「下一章」「目录」「书架」「设置」「评论」等）
- 将同一段落的断续行合并为连续文本
- 保留至少 50 个有效字符才返回成功

#### Scenario: 清洗移除 UI 噪声

- **WHEN** OCR 识别结果包含「上一章」「目录」等 UI 按钮文字和状态栏时间
- **THEN** 系统在清洗后移除这些噪声行，仅保留正文内容

#### Scenario: 清洗后文本不足

- **WHEN** 清洗后有效文本不足 50 个字符
- **THEN** 系统返回 422 错误，提示「未能从截图中提取到足够的文本，请确保截图包含正文内容」

#### Scenario: 段落合并

- **WHEN** OCR 将同一段正文识别为多行（如移动端窄列排版）
- **THEN** 系统将连续的中文行合并为完整的段落文本

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
