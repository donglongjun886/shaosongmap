## Why

起点读书App截图中的评论区上标数字（如 ¹²³、[1]、[23]）经 OCR 识别后会混入正文文本。这些孤立的数字标记干扰 LLM 对地名和军事行动的结构化提取，降低输出质量。

## What Changes

- 在 OCR 清洗管道（`_clean_text`）中新增评论标记移除步骤
- 实现 `_remove_comment_markers()` 函数，处理三种 OCR 识别形态：
  1. Unicode 上标数字（¹²³⁴⁵⁶⁷⁸⁹⁰）—— OCR 对上标字符的直接识别
  2. 方括号评论编号（[1]、[23]、[1,2]）—— 评论链接的文本表示
  3. 句末标点后的孤立数字（。14、。5、……122）—— OCR 将小号上标误识别为普通数字
- 第三种模式排除数字后紧跟数量词（万/千/百/十/余/数/两/几）的情况，避免误删正文中的真实数字

## Capabilities

### Modified Capabilities
- `screenshot-ocr`: OCR 清洗管道新增评论标记过滤，提升输出文本纯净度

## Impact

- `shaosongmap/ocr.py`：新增两个正则常量 + `_remove_comment_markers()` 函数，`_clean_text()` 中增加调用
- `tests/test_ocr.py`：新增 6 个测试用例覆盖三种模式及边界情况
