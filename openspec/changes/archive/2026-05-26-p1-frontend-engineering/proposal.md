## Why

`static/index.html` 是一个 1570 行的单文件巨石，HTML/CSS/JS 混杂，约 50 个函数和全局变量挤在同一作用域。编辑时需要在三种语言间频繁滚动，代码导航困难。maplibre-gl CDN 引用缺少 SRI integrity hash，存在供应链攻击风险。

## What Changes

- **拆分单文件巨石**：将 index.html 拆分为 HTML 骨架 + `css/map.css` + `js/map.js` + `js/utils.js` + `js/app.js`
- **CDN SRI 加固**：为 maplibre-gl JS 和 CSS 的 CDN 引用添加 integrity 属性
- **前端基础测试**：提取纯函数到 `js/utils.js`，用 pytest 编写单元测试
- 代码拆分后功能完全不变，所有现有行为保持兼容

## Capabilities

### New Capabilities

- `frontend-file-split`: 单文件 HTML 拆分为独立的 HTML/CSS/JS 文件，按功能模块组织
- `cdn-integrity`: CDN 资源引用添加 SRI integrity hash，防止供应链篡改
- `frontend-unit-tests`: 对纯函数（escHtml、_darkenColor、_factionColor、_computeDataDiagonal、_terrainColorForType）编写 pytest 单元测试

### Modified Capabilities

<!-- 无已有 spec 修改 -->

## Impact

- 重写 `static/index.html`（1570 → ~160 行骨架）
- 新增 `static/css/map.css`（~150 行）
- 新增 `static/js/map.js`（核心：地图初始化、底图、图标、comic 主题，~700 行）
- 新增 `static/js/utils.js`（纯函数：escHtml、颜色计算、距离计算等，~40 行）
- 新增 `static/js/app.js`（应用逻辑：OCR、提取、编辑、时间轴，~540 行）
- 新增 `tests/test_frontend_utils.py`（5-6 个纯函数单元测试）
- HTML 中 script 标签改为外部引用，加载顺序保证依赖关系