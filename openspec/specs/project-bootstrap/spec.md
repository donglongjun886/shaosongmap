# Project Bootstrap

## Purpose

项目基础配置与首次启动所需的一切——许可、README、前端工程化、CDN 安全。这些在项目初始化时设立，后续极少变更。

## Requirements

### Requirement: MIT 开源许可

系统 SHALL 在项目根目录提供 `LICENSE` 文件，包含完整的 MIT License 文本，覆盖 `shaosongmap/`、`app.py`、`static/`、`scripts/`、`tests/` 目录中的所有代码文件。

#### Scenario: 访问者查看许可

- **WHEN** 访问者打开仓库首页或 LICENSE 文件
- **THEN** 能看到 MIT License 全文，明确代码部分可自由使用、修改、分发，仅需保留版权声明

### Requirement: CHGIS 数据许可声明

系统 SHALL 在 README 的「许可说明」章节中单独声明 `data/chgis_v6/chgis_v6_points.csv` 的许可限制，明确该数据遵循 CHGIS v6 学术使用条款（免费用于学术/个人用途，商业使用需联系 Harvard Fairbank Center for Chinese Studies）。

#### Scenario: 使用者了解数据许可差异

- **WHEN** 使用者阅读 README 许可说明章节
- **THEN** 能清楚区分代码（MIT）和数据（CHGIS 学术许可）的不同使用范围

### Requirement: README 项目文档

系统 SHALL 在项目根目录提供 `README.md` 文件，包含项目名称、一句话描述、状态徽章和核心功能列表，使新访问者能在 30 秒内理解项目用途。

README MUST 包含：
- 项目名称和中文简介
- 状态徽章：CI 测试状态、Python 版本要求（3.10+）、License 类型
- 核心功能列表（截图 OCR、战役文本提取、古地名匹配、地图渲染）
- 从零到运行的完整步骤（环境要求、依赖安装、环境变量配置、启动命令、访问地址）
- 项目目录结构和关键文件用途
- 主要 API 端点及其用途

#### Scenario: 首次访问者理解项目

- **WHEN** 访问者打开 GitHub 仓库首页
- **THEN** 能在 README 顶部看到项目名称、徽章、简介和功能列表

#### Scenario: 新开发者成功启动项目

- **WHEN** 开发者按 README 步骤操作
- **THEN** 能在本地成功启动服务并在浏览器中看到功能界面

#### Scenario: 开发者快速定位代码

- **WHEN** 开发者需要修改某个功能
- **THEN** 能通过项目结构说明快速找到对应的源码文件

### Requirement: CDN 资源 SRI 完整性校验

所有从 CDN 加载的外部资源 MUST 添加 `integrity` 属性和 `crossorigin="anonymous"` 属性。

受影响的资源 SHALL 包括：
- `maplibre-gl@4.7.1` JavaScript 库
- `maplibre-gl@4.7.1` CSS 样式表

#### Scenario: CDN 脚本带 SRI hash

- **WHEN** 查看 `index.html` 中 maplibre-gl JS 的 `<script>` 标签
- **THEN** 该标签包含 `integrity="sha384-..."` 和 `crossorigin="anonymous"` 属性

#### Scenario: hash 不匹配时浏览器拒绝加载

- **WHEN** CDN 返回的内容与 SRI hash 不匹配
- **THEN** 浏览器拒绝执行该资源，控制台输出 SRI 校验失败错误

### Requirement: 前端代码文件拆分

项目 MUST 将前端代码按关注点拆分为独立的 CSS/JS 文件：
- `static/index.html` 仅包含 HTML 骨架和外部资源引用
- CSS 样式独立为 `static/css/map.css`
- JS 逻辑按纯函数/渲染层/交互层拆分为 `static/js/utils.js`、`static/js/map.js`、`static/js/app.js`
- HTML 中 script 标签按 utils.js → map.js → app.js 的顺序加载

#### Scenario: 页面正常加载

- **WHEN** 浏览器加载 `static/index.html`
- **THEN** 页面样式与交互功能与拆分前完全一致

#### Scenario: 无内联代码块

- **WHEN** 查看拆分后的 `index.html` 源码
- **THEN** 不存在 `<style>` 块和 `<script>` 代码块

### Requirement: 前端纯函数单元测试

项目 MUST 对 `static/js/utils.js` 中无 DOM 依赖的纯函数提供 pytest 单元测试，覆盖 `escHtml`、`_darkenColor`、`_factionColor`、`_computeDataDiagonal`、`_terrainColorForType` 五个函数。

测试文件放置于 `tests/test_frontend_utils.py`。

#### Scenario: escHtml 转义 HTML 特殊字符

- **WHEN** 输入 `"<script>alert('xss')</script>"`
- **THEN** 输出特殊字符被转义为 HTML 实体

#### Scenario: _factionColor 阵营识别

- **WHEN** 输入 `"宋军主力"`
- **THEN** 返回 `"#2b4c7e"`（宋色）
- **WHEN** 输入 `"金兵前锋"`
- **THEN** 返回 `"#c23b22"`（金色）
