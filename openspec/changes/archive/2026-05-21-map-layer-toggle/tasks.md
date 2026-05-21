## 1. 图层拆分

- [x] 1.1 将 `place-labels` 单层拆分为 `place-labels-ancient` 和 `place-labels-modern` 两个独立 symbol 层，分别设置 text-field、text-offset 和样式
- [x] 1.2 移除旧的 `place-labels` 层定义

## 2. 图例面板改造

- [x] 2.1 在图例区 `.legend` 中新增 checkbox 控件，包含「古地名」和「今地名对照」两个开关
- [x] 2.2 为 checkbox 控件编写 CSS 样式，保持与现有图例风格一致

## 3. 交互逻辑

- [x] 3.1 实现 checkbox onChange 事件，通过 `map.setLayoutProperty` 切换对应图层的 visibility
- [x] 3.2 图层默认状态均为 visible，与现有行为一致

## 4. 验证

- [x] 4.1 启动服务，在浏览器中验证图层切换功能正常：切换古/今名标签显隐，确认标记圆点不受影响
- [x] 4.2 验证重新渲染后图层开关状态保持