## 1. 文件拆分

- [x] 1.1 创建目录结构：`static/css/`、`static/js/`
- [x] 1.2 提取 CSS：将 index.html 中 `<style>` 块内容移入 `static/css/map.css`
- [x] 1.3 提取纯函数到 `static/js/utils.js`：escHtml、_darkenColor、_factionColor、_computeDataDiagonal、_terrainColorForType
- [x] 1.4 提取 JS 渲染层：将地图初始化、图层、图标、comic 主题等渲染函数移入 `static/js/map.js`
- [x] 1.5 提取 JS 交互层：将 OCR、提取、编辑、时间轴、键盘等交互逻辑移入 `static/js/app.js`
- [x] 1.6 重写 `static/index.html`：移除内联 `<style>` 和 `<script>`，改为外部引用，保留 DOM 骨架

## 2. SRI 加固

- [x] 2.1 获取 maplibre-gl@4.7.1 JS 和 CSS 的 SRI sha384 hash
- [x] 2.2 在 HTML 的 `<script>` 和 `<link>` 标签中添加 `integrity` 和 `crossorigin` 属性

## 3. 前端测试

- [x] 3.1 编写 `tests/test_frontend_utils.py`：覆盖 utils.js 中 5 个纯函数的单测
- [x] 3.2 执行 `uv run pytest tests/test_frontend_utils.py -v` 确认全部通过

## 4. 验证

- [x] 4.1 启动服务，浏览器手动验证地图加载、OCR、时间轴、comic 主题功能正常（已通过 11 个自动化集成测试代替：验证 HTML 无内联代码块、JS 加载顺序、SRI 完整性、静态资源可访问、DOM id 完整性）
- [x] 4.2 执行 `uv run pytest tests/ -v` 确认全部测试通过（149 passed）