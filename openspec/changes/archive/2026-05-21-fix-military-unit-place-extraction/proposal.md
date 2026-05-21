## Why

LLM在提取地名时会将含地名的军队编制名（如"秦凤路大军"、"泾原路兵马"）中的行政区划成分错误提取为places，导致地图上出现本应是军队标识的虚假地点标记。该问题直接影响地图准确性和用户信任度，需在文本提取层修复。

## What Changes

- 在两个System Prompt中新增排除规则：明确告知LLM，当行政区划名作为军队编制名称的一部分出现时（如"X路大军"、"X州兵马"），不应将其提取为places
- 在`extract()`和`extract_timeline()`中增加后处理过滤函数，对LLM返回的places做二次校验，过滤掉上下文明确属于军队编制的地名
- `Place`模型新增可选`place_type`字段，区分地名类型（城池、关隘、行政区、山川等），为后续山川河流可视化做准备

## Capabilities

### New Capabilities
<!-- None for this change -->

### Modified Capabilities
- `campaign-text-extraction`: 新增军队编制名排除规则，确保places列表中不包含仅作为军队修饰语出现的地名

## Impact

- `shaosongmap/extractor.py`：两个System Prompt + 新增后处理过滤函数
- `shaosongmap/models.py`：Place模型新增可选`place_type`字段
- `tests/test_extractor.py`：新增针对军队编制名过滤的测试用例
