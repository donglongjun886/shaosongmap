## Why

项目计划公开作为技术展示，当前缺少开源许可证（LICENSE 文件）和数据许可声明，访问者无法明确代码和数据的合法使用范围。代码部分应采用 MIT 协议，CHGIS 数据部分需单独标注学术使用限制。

## What Changes

- 新增 `LICENSE` 文件：MIT License，覆盖项目代码部分
- 修改 `README.md`：在末尾补充「许可说明」章节，区分代码协议（MIT）和数据协议（CHGIS v6 学术许可）

## Capabilities

### New Capabilities
- `project-license`: 项目开源许可证和数据许可声明

### Modified Capabilities
- `project-readme`: 新增「许可说明」章节，声明代码和数据的双重许可

## Impact

- `LICENSE`: **新增** 项目根目录
- `README.md`: **修改** 末尾新增许可说明章节
- 无代码变更、API 变更、依赖变更