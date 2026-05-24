## 1. 前端——底图 Provider 架构

- [x] 1.1 重构地图初始化：style layers 改为空数组，动态添加逻辑集中在 `map.on('load')`
- [x] 1.2 实现 `BASEMAP` provider 注册表（schematic + muted_osm）和 `applyBasemap(name)` 切换函数
- [x] 1.3 实现 scale 自动选择底图逻辑（tactical→schematic, battle/strategic→muted_osm）
- [x] 1.4 预留 `basemapMode` 手动切换接口（变量 + 注释），不实现 UI

## 2. 前端——Zoom 响应式标记

- [x] 2.1 地名 circle-radius 改为 zoom step 表达式（3/6/10/14px 分段）
- [x] 2.2 地名 text-size 改为 zoom step 表达式（9/11/13/15px 分段）
- [x] 2.3 灰显（dim）标记 circle-radius 比正常小 2px

## 3. 后端——箭头形状优化

- [x] 3.1 `_make_block_arrow_polygon`：宽长比从 1:2 改为 1:3.5，头部占比从 27% 改为 40%
- [x] 3.2 `_make_unit_geojson`：尺寸参数改为基于 scale 系数的统一计算（移除固定 400/2000/5000 米制）

## 4. 后端——箭头尺寸自适应

- [x] 4.1 实现 `_compute_data_diagonal(place_coords)` 计算数据包围盒对角线长度
- [x] 4.2 `_make_unit_geojson`：箭头尺寸 = diagonal × scale_ratio（tactical 0.20 / battle 0.08 / strategic 0.03）
- [x] 4.3 最小像素保底：估算 40px 对应地理距离，body_len 不低于此值
- [x] 4.4 `_compute_unit_offsets`：偏移间距随新的箭头宽度自适应调整

## 5. TODO 占位

- [x] 5.1 在 `map.on('load')` 末尾添加 Phase 3 山川河流符号层占位注释
- [x] 5.2 更新 `project_next_features.md` 将「示意图风格」标记为 Phase 2 完成，添加 Phase 3 待讨论

## 6. 验证

- [x] 6.1 启动应用，确认 tactical 级别使用纯色底图，battle/strategic 使用低饱和 OSM
- [x] 6.2 测试不同数据范围（单点、局部、大范围）下箭头尺寸合理
- [x] 6.3 测试 zoom 变化时地名标记尺寸平滑过渡