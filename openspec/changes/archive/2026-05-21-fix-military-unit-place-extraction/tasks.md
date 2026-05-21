## 1. 数据模型

- [x] 1.1 Place 模型新增可选 `place_type` 字段（枚举：city/mountain_pass/river/mountain/region/battlefield）

## 2. Prompt 增强

- [x] 2.1 `_SYSTEM_PROMPT` 新增军队编制名排除规则（第9条）
- [x] 2.2 `_TIMELINE_SYSTEM_PROMPT` 同步新增军队编制名排除规则（第10条）
- [x] 2.3 两个 Prompt 中 Place schema 新增 `place_type` 可选字段说明

## 3. 后处理过滤

- [x] 3.1 实现 `_filter_military_unit_places()` 函数，基于 context 字段匹配军队编制后缀并过滤
- [x] 3.2 在 `extract()` 返回前调用过滤函数
- [x] 3.3 在 `extract_timeline()` 返回前调用过滤函数

## 4. 测试

- [x] 4.1 编写「军队编制名不被提取为地名」的单元测试
- [x] 4.2 编写「后处理过滤」的单元测试
- [x] 4.3 编写「place_type 字段」的单元测试
- [x] 4.4 运行全量测试确认无回归
