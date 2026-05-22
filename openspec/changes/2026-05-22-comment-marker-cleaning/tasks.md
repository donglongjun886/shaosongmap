## 1. 实现

- [x] 1.1 新增三个正则常量：`_SUPERSCRIPT_DIGITS`、`_BRACKET_COMMENT`、`_POST_PUNCT_DIGITS`
- [x] 1.2 实现 `_remove_comment_markers()` 函数，依次应用三个正则
- [x] 1.3 在 `_clean_text()` 合并行之后调用 `_remove_comment_markers()`
- [x] 1.4 更新 `_clean_text()` docstring 补充第5条清洗规则

## 2. 测试

- [x] 2.1 Unicode 上标数字移除
- [x] 2.2 方括号评论编号移除
- [x] 2.3 句号后孤立数字移除
- [x] 2.4 省略号后评论数字移除
- [x] 2.5 真实起点文本片段验证
- [x] 2.6 数量词边界保护（5万、10余）
- [x] 2.7 `_clean_text` 集成测试
- [x] 2.8 无标记文本原样返回
