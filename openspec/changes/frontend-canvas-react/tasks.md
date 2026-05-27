## 1. P0: Canvas 渲染引擎

- [ ] 1.1 新增 `static/js/canvasRenderer.js`：Canvas 覆盖层初始化、resize 同步、rAF 渲染循环 + 脏标记
- [ ] 1.2 实现 `map.project()` 坐标转换 + 视口裁剪（仅绘制屏幕内元素）
- [ ] 1.3 实现兵牌卡片绘制函数（圆角矩形、双层边框、顶部色条、文字、dropShadow）
- [ ] 1.4 实现进攻箭头绘制函数（14px 线宽、3:2 头部、微弧贝塞尔、阵营色 + 黑色描边）
- [ ] 1.5 实现同坐标多部队像素偏移（按 `_slot` 沿南北排列，64px 间距，对称分布）
- [ ] 1.6 实现碰撞避让（AABB 检测，兵牌与地名标记重叠时优先向北偏移）

## 2. P0: 清理旧渲染代码

- [ ] 2.1 `map.js` 删除 `_applyUnitOffsets()` 函数及所有调用
- [ ] 2.2 `map.js` 删除 `_onMapMoved` 偏移重算监听
- [ ] 2.3 `map.js` 删除 `unit-banners` 和 `comic-unit-icons` MapLibre source/layer
- [ ] 2.4 `map.js` 删除 `_renderComicUnitMarkers()` 函数
- [ ] 2.5 `map.js` 接入 Canvas 渲染器（`updateMap()` 中调用 `canvasRenderer.setData()` + `markDirty()`）
- [ ] 2.6 `shaosongmap/services/unit_banner.py` 删除 `compute_unit_offsets()` 及相关代码
- [ ] 2.7 `shaosongmap/services/unit_banner.py` 坐标保持真实值，仅添加 `_slot` 序号字段
- [ ] 2.8 更新 `tests/` 中引用 `compute_unit_offsets` 的测试用例

## 3. P0: 状态动画

- [ ] 3.1 实现部队首次出现生长动画（箭头 600ms 逐步绘制 + 兵牌 opacity 渐变）
- [ ] 3.2 实现交战状态脉冲动画（边框颜色渐变 + 3 次缩放脉冲）
- [ ] 3.3 实现溃散碎裂动画（opacity 递减 + 箭头碎裂为 8 个随机散点淡出）

## 4. P0: MapLibre move/zoom 事件集成

- [ ] 4.1 `map.on('moveend')` 回调中调用 `canvasRenderer.markDirty()`
- [ ] 4.2 `map.on('zoomend')` 回调中检查尺度级别切换，更新渲染策略
- [ ] 4.3 `map.on('resize')` 回调中同步 Canvas 元素尺寸

## 5. P0: 主题配置

- [ ] 5.1 提取阵营色/兵牌尺寸/箭头参数为 JS 配置对象 `THEME_CONFIG`
- [ ] 5.2 支持 comic 主题完整参数 + battle/strategic 简化参数两套配置
- [ ] 5.3 根据 `scale` 字段自动选择配置（tactical → comic, battle/strategic → simplified）

## 6. P0: 自测验证

- [ ] 6.1 手动测试：输入默认战役文本，验证兵牌渲染正确（数量/位置/颜色）
- [ ] 6.2 手动测试：缩放地图，验证兵牌跟随、无抖动、无重叠
- [ ] 6.3 手动测试：时间轴步进，验证部队状态动画正常
- [ ] 6.4 运行 `python scripts/selftest.py`，程序化检查 + Qwen-VL 视觉验证
- [ ] 6.5 运行 `uv run pytest tests/ -v --cov=shaosongmap`，确保测试全部通过

## 7. P1: LLM 地形推理

- [ ] 7.1 新增 `shaosongmap/terrain.py`：LLM 地形特征提取模块
- [ ] 7.2 在 `/api/extract` 管道中集成地形推理（或新增 `/api/terrain` 端点）
- [ ] 7.3 扩展 Pydantic 模型：新增 `TerrainFeature` 数据模型
- [ ] 7.4 编写地形提取单元测试

## 8. P1: Canvas 地形渲染

- [ ] 8.1 新增 `static/js/terrainRenderer.js`：Canvas 地形绘制模块
- [ ] 8.2 实现塬地渲染（浅棕绿圆角矩形 + 边缘披麻皴短竖线）
- [ ] 8.3 实现坡地渲染（渐变填充 + 稀疏短竖线）
- [ ] 8.4 实现河沟渲染（蓝色虚线曲线）
- [ ] 8.5 实现谷地渲染（浅黄 V 形填充）
- [ ] 8.6 实现地形 zoom 自适应（tactical 完整 → battle 简化 → strategic 仅色块）
- [ ] 8.7 确保地形 z-index：底图 < 地形 < 路线 < 兵牌 < 地名

## 9. P2: React 基础设施

- [ ] 9.1 新增 `package.json`（esbuild + React 18 依赖）
- [ ] 9.2 新增 esbuild 构建脚本（`static/js/react/` → `static/js/react-bundle.js`）
- [ ] 9.3 新增 `static/js/react/index.jsx`：React 根组件 + 挂载点
- [ ] 9.4 新增 `static/js/react/EventBus.js`：EventTarget 事件总线模块
- [ ] 9.5 `static/index.html` 添加 `#react-ui` 容器 + 引用 `react-bundle.js`

## 10. P2: React UI 组件

- [ ] 10.1 实现 `Timeline` 组件（进度条节点 + 步进按钮 + 播放/暂停 + 键盘快捷键）
- [ ] 10.2 实现 `EventCard` 组件（事件序号/类型/描述/涉及部队和地名）
- [ ] 10.3 实现 `Legend` 组件（图层 checkbox + 颜色预览）
- [ ] 10.4 实现 `Toolbar` 组件（缩放按钮 + 复位 + 截图导出）
- [ ] 10.5 实现 `UnitList` 组件（部队状态卡片列表 + 点击高亮地图）
- [ ] 10.6 `app.js` 中删除被 React 替代的 UI 操作代码

## 11. P3: 多尺度渲染

- [ ] 11.1 实现四级尺度分类函数 `getScaleLevel(zoom)`：siege/tactical/battle/strategic
- [ ] 11.2 实现底图动态切换（纯色背景 ↔ OpenFreeMap 瓦片，带滞回带）
- [ ] 11.3 实现部队兵牌尺度自适应（完整卡片 → 简化 → 圆点编号）
- [ ] 11.4 实现行军路线尺度自适应（粗实线 → 虚线 → 细虚线）
- [ ] 11.5 实现地名标签密度自适应（全部 → 重要 → 仅城市）

## 12. 收尾

- [ ] 12.1 运行全量质量门禁：`uv run pre-commit run --all-files`
- [ ] 12.2 运行全量测试：`PYTHONPATH=. uv run pytest tests/ -v --cov=shaosongmap`
- [ ] 12.3 代码审查：调用 `review_code` MCP 工具做异源审查
- [ ] 12.4 端到端自测：调用 `run_e2e_test` MCP 工具验证前端渲染
