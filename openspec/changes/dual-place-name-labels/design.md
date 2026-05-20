## Context

当前 `place-labels` 图层仅显示古地名（`text-field: ['get', 'name']`），modern_name 仅在 popup 中展示。需要改为双行标签：古名主标 + 今名副标。

## Goals / Non-Goals

**Goals:**
- CHGIS 精确匹配的地名显示「古名\n今名」双行标签
- LLM 推断地名保持单行标签（无 modern_name 可显示）
- 古名和今名视觉上有区分（字号/颜色）
- 不改动 popup 行为（popup 内容保持不变）

**Non-Goals:**
- 不改后端 API
- 不改 GeoJSON 数据结构
- 不改 LLM 推断 label

## Decisions

### 1. 标签格式方案

**选择**: 使用 MapLibre `text-field` 表达式，根据 `modern_name` 是否为空动态切换单/双行。

```javascript
'text-field': [
  'case',
  ['!=', ['get', 'modern_name'], ''],
  ['concat', ['get', 'name'], '\n', ['get', 'modern_name']],
  ['get', 'name']
]
```

**理由**: 
- 纯前端改动，无后端依赖
- `case` 表达式在 MapLibre 原生支持，性能无影响
- LLM 推断地名（modern_name 为空）自动退化为单行

### 2. 字体层次

**选择**: 整个标签统一字号（12px），古名用深色（#1a1a1a），今名用灰色（#888）。

但 MapLibre `text-field` 的简单 `concat` 无法对第二行单独着色。替代方案：
- 使用 `format` 表达式实现分行分色 → **选择此方案**
- 或统一颜色+稍小字号（11px），靠换行区分层次

```javascript
'text-field': [
  'case',
  ['!=', ['get', 'modern_name'], ''],
  ['format',
    ['get', 'name'], { 'text-color': '#1a1a1a', 'text-font': ['bold'] },
    '\n',
    ['get', 'modern_name'], { 'text-color': '#888888', 'text-font': ['italic'] }
  ],
  ['get', 'name']
]
```

### 3. 标签定位

保持 `text-offset: [0, 1.5]`（标记下方），确保不与 circle 重叠。

## Risks / Trade-offs

- 长地名标签重叠 → 保持 12px 字号，地图缩放后自然分散