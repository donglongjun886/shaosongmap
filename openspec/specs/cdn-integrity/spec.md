# cdn-integrity

**Purpose**: 通过 SRI (Subresource Integrity) 防止 CDN 资源被篡改，保障前端供应链安全。

## Requirements

### Requirement: CDN 资源 SRI 完整性校验

所有从 CDN 加载的外部资源 MUST 添加 `integrity` 属性和 `crossorigin="anonymous"` 属性。

受影响的资源 SHALL 包括：
- `maplibre-gl@4.7.1` JavaScript 库
- `maplibre-gl@4.7.1` CSS 样式表

#### Scenario: CDN 脚本带 SRI hash

- **WHEN** 查看 `index.html` 中 maplibre-gl JS 的 `<script>` 标签
- **THEN** 该标签包含 `integrity="sha384-..."` 和 `crossorigin="anonymous"` 属性

#### Scenario: CDN 样式带 SRI hash

- **WHEN** 查看 `index.html` 中 maplibre-gl CSS 的 `<link>` 标签
- **THEN** 该标签包含 `integrity="sha384-..."` 和 `crossorigin="anonymous"` 属性

#### Scenario: hash 不匹配时浏览器拒绝加载

- **WHEN** CDN 返回的内容与 SRI hash 不匹配（文件被篡改或版本变更）
- **THEN** 浏览器拒绝执行该资源，控制台输出 SRI 校验失败错误