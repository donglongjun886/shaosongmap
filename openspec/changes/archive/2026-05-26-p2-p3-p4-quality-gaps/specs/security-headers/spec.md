# Security Headers 安全响应头

## ADDED Requirements

### Requirement: Content-Security-Policy 响应头

系统 SHALL 在每次 HTTP 响应中添加 `Content-Security-Policy` 头。

CSP 策略 MUST 满足以下约束：
- `default-src 'self'`
- `script-src` 允许 `'self'` 及 CDN 来源（`cdn.jsdelivr.net`、`unpkg.com`）
- `style-src` 允许 `'self'`、`'unsafe-inline'` 及 CDN 来源
- `img-src` 允许 `'self'`、`data:`、`blob:` 及 OpenStreetMap 瓦片域
- `connect-src 'self'`
- `font-src` 允许 `'self'` 及 CDN 来源

#### Scenario: 页面请求包含 CSP 头

- **WHEN** 客户端 GET 首页 `/`
- **THEN** 响应头包含 `Content-Security-Policy`，值包含 `default-src 'self'`

#### Scenario: API 请求包含 CSP 头

- **WHEN** 客户端 POST `/api/v1/extract`
- **THEN** 响应头包含 `Content-Security-Policy`

#### Scenario: CSP 允许合法 CDN 脚本

- **WHEN** 前端加载 `https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.js`
- **THEN** 浏览器不因 CSP 策略阻止该脚本

#### Scenario: CSP 阻止未知来源脚本

- **WHEN** 恶意脚本尝试从 `https://evil.com/malicious.js` 加载
- **THEN** 浏览器根据 CSP 策略阻止该脚本执行

### Requirement: 安全头中间件实现

CSP 中间件 SHALL 通过 Starlette middleware 实现，MUST 遵循以下设计：

- 通过 `@app.middleware('http')` 注册
- 使用 `SECURITY_HEADERS` 配置字典集中管理
- 日志记录 middleware 注册事件

#### Scenario: 中间件不影响正常请求

- **WHEN** 任意合法请求进入
- **THEN** 中间件在响应中添加安全头后正常返回，请求处理不受影响