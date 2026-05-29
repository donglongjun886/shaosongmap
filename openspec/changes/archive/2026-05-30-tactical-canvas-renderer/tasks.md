## 1. 创建 TacticalRenderer 模块

- [x] 1.1 创建 IIFE 骨架、THEME 配置、内部状态变量
- [x] 1.2 实现 `_collectAllCoords(data)` 收集所有数据点经纬度
- [x] 1.3 实现 `_computeProjection(coords, cw, ch)` 包围盒计算 + 等比缩放 + 除零兜底
- [x] 1.4 实现 `_project(lng, lat)` 经纬度→Canvas 像素映射函数
- [x] 1.5 复刻 `_drawArrow`、`_drawFlag`、`_factionColor`、`_loadBannerImages`（加 TODO 备注后续抽 renderUtils.js）
- [x] 1.6 实现 `_render()` 单 Canvas 绘制管线（背景→路线→地名→旗帜→箭头→标签）
- [x] 1.7 实现多点环形分布 `_applyCircularOffset(slot, total)` 避免部队图标重叠
- [x] 1.8 实现 `init(container)`：创建 Canvas、DPR 设置、Resize 监听
- [x] 1.9 实现 `setData(geojson)`：收集坐标→算投影→调用 `_render()`
- [x] 1.10 实现 `setTimeline(step, total)`：时间轴过滤 + 重绘
- [x] 1.11 实现 `destroy()`：移除 Canvas、解绑事件、清理引用

## 2. 修改现有文件

- [x] 2.1 修改 `app.js`：handleSSEEvent 和 reRender 中按 `scale === 'tactical'` 分叉调用 TacticalRenderer
- [x] 2.2 修改 `index.html`：`<script src="js/tacticalRenderer.js"></script>` 在 roughjs 之后引入

## 3. 验证

- [ ] 3.1 输入 Tactical 级战役文本，确认 TacticalRenderer 接管渲染
- [ ] 3.2 确认箭头起终点在 Canvas 范围内，无裁剪
- [ ] 3.3 确认 Battle 级战役走旧路径不受影响
- [ ] 3.4 确认高分屏（Retina）渲染清晰
- [ ] 3.5 确认多点同坐标时环形分布不重叠
- [ ] 3.6 确认窗口 resize 后重绘正确
