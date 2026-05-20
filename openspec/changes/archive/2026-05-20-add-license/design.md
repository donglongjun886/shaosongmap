## Context

项目当前无 LICENSE 文件，处于 "All Rights Reserved" 默认状态。计划公开为技术展示项目，需要明确开源许可。此外，CHGIS v6 数据有独立的学术使用限制，需与代码协议分开声明。

## Goals / Non-Goals

**Goals:**
- 为代码部分添加 MIT License
- 在 README 中区分代码许可和数据许可
- 确保 CHGIS 数据使用合规

**Non-Goals:**
- 不添加 CONTRIBUTING.md、CODE_OF_CONDUCT.md（个人项目不需要）
- 不修改 CHGIS 数据本身的许可条款

## Decisions

### 1. 代码许可选择 MIT

**选择**: MIT License

**理由**: 
- GitHub 上最广泛使用的许可，简单明了
- 对使用者限制最少（署名即可，允许商用、修改、再发布）
- 适合技术展示项目，不会吓跑潜在关注者

**替代方案**:
- GPLv3 → 要求衍生作品也开源，过度限制，不推荐用于展示项目
- Apache 2.0 → 比 MIT 多了专利授权和商标保护，对小型个人项目过度
- 不加 LICENSE → 默认保留所有权利，fork 都不合法

### 2. 代码和数据双重许可声明

**选择**: LICENSE 文件放 MIT 全文，README 末尾新增「许可说明」章节，注明：
- 代码部分：MIT License
- 数据部分（CHGIS v6）：仅限学术/个人用途，商业使用需联系 Harvard Fairbank Center

**理由**: 
- 避免混淆：让使用者明确哪些文件适用哪种许可
- CHGIS 合规：CHGIS 明确禁止商业使用，不能放在 MIT 下

## Risks / Trade-offs

- MIT 允许商用 → 与 CHGIS 数据的 academic-only 许可存在张力 → 用 README 明确区分已足够