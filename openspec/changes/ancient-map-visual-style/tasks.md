## 1. 第一轮：配色 + 字体 (P1+P2)

- [x] 1.1 CSS 色板变量定义：宣纸色 #f2e8d5 / 朱砂 #c23b22 / 靛蓝 #2b4c7e / 赭石 #8b4513 / 墨色 #2c2c2c / 青灰 #5a7a6a
- [x] 1.2 全局字体切换为衬线中文字体系列（KaiTi/Songti SC/Noto Serif SC/SimSun/Serif 回退栈）
- [x] 1.3 地图图层配色更新：部队阵营色、路线色、地名标签色、图例色
- [x] 1.4 Panel 面板配色更新：header 背景、文字色、边框色适配古地图风格

## 2. 第二轮：地名图标 (P3)

- [x] 2.1 实现 Canvas 离屏渲染函数：生成城池图标（双线方框）和营寨图标（三角）
- [x] 2.2 在 `map.on('load')` 中注册图标：`map.addImage('fortress', ...)` / `map.addImage('camp', ...)`
- [x] 2.3 地名图层从 `circle` 迁移为 `symbol`：使用 `icon-image` + `icon-size` zoom 表达式
- [x] 2.4 灰显地名图层同步迁移为 symbol + `icon-opacity` 控制

## 3. 第三轮：路线 + 纹理 + 边框 (P4+P5+P6)

- [x] 3.1 路线样式：实线改朱砂色虚线（line-dasharray: [4,3]），大箭镞图标替换 unicode ▶
- [x] 3.2 地图背景叠加 SVG noise 纹理（CSS ::after + feTurbulence filter）
- [x] 3.3 地图区域添加卷轴边框（2px solid 墨色 + 内阴影）
- [x] 3.4 图例面板样式适配古地图风格

## 4. 验证

- [x] 4.1 启动应用，验证 tactical 级别地名显示为城池/营寨图标
- [x] 4.2 验证 battle/strategic 级别配色、字体、纹理、边框整体协调
- [x] 4.3 验证 104 个测试仍全部通过
