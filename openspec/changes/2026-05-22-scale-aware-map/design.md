## 设计决策

### 尺度判断：LLM 推断，非规则推断

选择由 LLM 在 extract 阶段一并输出 scale，而非基于地名数量/路线长度的规则推断：

- LLM 能理解语义（"五路大军会战"是 strategic，"单部遭遇"是 tactical）
- 规则法在边界 case 上容易误判（3 个地名可能是战术也可能是战役，取决于空间跨度）
- 增量成本几乎为零（一个字段，~5 token）

### 三级尺度 vs 更多的细分

选择三级而非五级（如增加 operational、grand-strategic）：

- 三类文本在历史小说中是最清晰可辨的
- 三级对应的 maxZoom 差距足够大（14 vs 10 vs 6），渲染差异明显
- 更多级别增加 LLM 分类的不确定性

### 前端 maxZoom 策略

| scale | maxZoom | 效果 |
|-------|---------|------|
| tactical | 14 | fitBounds 后允许缩到街区级，底图呈现地形细节 |
| battle | 10 | 当前默认行为，保持向后兼容 |
| strategic | 6 | 限制缩入，保持州府以上的全局视野 |
| null | 10 | 兼容旧响应，降级到 battle 行为 |

### 重新渲染路径

`collectModifiedData()` 回传 `_lastExtractData.scale`，确保用户编辑地点/路线后重新渲染时 scale 不丢失。
