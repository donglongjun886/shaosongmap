## 1. 底图替换

- [x] 1.1 修改 `static/index.html` 地图初始化 style 对象：移除 OSM raster 瓦片 source 和 osm-layer，替换为 `background` 图层（颜色 `#f5f0e1`）

## 2. 验证

- [x] 2.1 启动应用，确认地图渲染为仿古纸淡黄背景，无外部瓦片请求，所有数据层正常显示