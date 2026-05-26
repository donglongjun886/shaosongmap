# frontend-file-split

**Purpose**: 确保前端代码按关注点拆分为独立的 CSS/JS 文件，提高可维护性。

## Requirements

### Requirement: 前端代码文件拆分

项目 MUST 将 `static/index.html` 拆分为独立的 HTML、CSS、JS 文件。

拆分后 SHALL 满足：
- `static/index.html` 仅包含 HTML 骨架和外部资源引用
- CSS 样式独立为 `static/css/map.css`
- JS 逻辑按纯函数/渲染层/交互层拆分为 `static/js/utils.js`、`static/js/map.js`、`static/js/app.js`
- HTML 中 script 标签按 utils.js → map.js → app.js 的顺序加载，保证依赖关系
- 所有现有功能行为不变：地图初始化、底图切换、图标渲染、comic 主题、批量 OCR、SSE 提取、可编辑面板、时间轴交互、图层切换、键盘快捷键

#### Scenario: 页面正常加载

- **WHEN** 浏览器加载 `static/index.html`
- **THEN** 页面样式与交互功能与拆分前完全一致，地图正常显示

#### Scenario: 批量 OCR 功能正常

- **WHEN** 用户上传截图并执行批量 OCR
- **THEN** SSE 进度回调、文本合并、编辑确认流程与拆分前行为一致

#### Scenario: 时间轴交互正常

- **WHEN** 用户在时间轴模式下点击前/后步进按钮
- **THEN** 地图要素过滤、事件卡片、部队状态卡片正确更新

### Requirement: HTML 骨架精简

拆分后的 `index.html` MUST 仅保留 HTML 骨架和外部资源引用。

HTML 文件 SHALL:
- 通过 `<link rel="stylesheet">` 引用外部 CSS
- 通过 `<script src>` 引用外部 JS，不包含内联 `<style>` 或 `<script>` 代码块
- 保留所有 DOM 元素 id 不改变，保证 JS 选择器兼容

#### Scenario: 无内联代码块

- **WHEN** 查看拆分后的 `index.html` 源码
- **THEN** 不存在 `<style>` 块和 `<script>` 代码块（允许正常 script src 引用标签）