## 1. CSS 基础设施

- [x] 1.1 在 `static/index.html` 中定义阵营色 CSS 自定义属性（`--faction-song`、`--faction-jin`、`--faction-unknown`、`--status-engaging`）
- [x] 1.2 定义 `.theme-comic` CSS class，作用域为地图容器内所有相关元素
- [x] 1.3 在 JS 中添加 scale 判断逻辑：管道返回 `tactical` 时给 map 容器添加 `.theme-comic` class

## 2. 阵营色系统

- [x] 2.1 修改部队标记渲染函数，根据 faction 字段映射到对应的 CSS 阵营色变量
- [x] 2.2 修改行军路线渲染，箭头颜色从硬编码改为阵营色变量引用
- [x] 2.3 修改方向指示线渲染，线色跟随阵营色

## 3. Tactical 字体切换

- [x] 3.1 在 `.theme-comic` 下设置 MapLibre 文字标签 font-family 为宋体系列
- [x] 3.2 验证左侧面板字体不受 comic 主题影响（保持楷体）

## 4. 地形色块

- [x] 4.1 实现 `place_type` → 色块颜色的映射函数
- [x] 4.2 以地名坐标为中心生成 GeoJSON fill layer source（半径 = 数据对角线 × 5%）
- [x] 4.3 添加 MapLibre fill layer，z-index 在底图之上、路线之下
- [x] 4.4 仅在 comic 主题激活时显示地形色块 layer

## 5. Comic 风格部队标记

- [x] 5.1 实现 Canvas 离线生成阵营色填充矩形框 icon 的函数（阵营色底 + 白字 + 同色系深边框）
- [x] 5.2 通过 MapLibre `addImage()` 为每个部队注册 icon，使用 `image` 类型 symbol layer 渲染
- [x] 5.3 添加 scale 判断：tactical 级用 comic 标记，battle/strategic 级保持双线套框
- [x] 5.4 图例中「部队旗帜」文案在 comic 主题下改为「部队标记」

## 6. 箭头加粗与笔触感

- [x] 6.1 Comic 主题下行军路线线宽设为 3.5px，`line-cap: round`
- [x] 6.2 路线起点添加圆形顿笔点（MapLibre circle layer，直径 = 线宽 × 1.8）
- [x] 6.3 末端箭头尺寸放大 20%

## 7. 红色印章装饰

- [x] 7.1 在地图容器内添加 `position: absolute` 的印章 div
- [x] 7.2 实现内联 SVG 印章：正方形边框 + 白文风格文字 + 约 15 度旋转
- [x] 7.3 根据 campaign_name 填充印章文字（最多 4 字），无战役名时隐藏

## 8. 地名标签光晕

- [x] 8.1 Comic 主题下设置 MapLibre 地名标签的 text-halo 属性（白色 75% 透明 + 2.5px 宽）
- [x] 8.2 验证标签在地形色块上方的可读性

## 9. 集成验证

- [x] 9.1 用 tactical 级战役文本测试完整 pipeline，验证 comic 主题自动激活
- [x] 9.2 用 battle 级战役文本测试，验证现有样式不受影响
- [x] 9.3 用 Qwen-VL Review 模式截图审查 comic 主题视觉效果
