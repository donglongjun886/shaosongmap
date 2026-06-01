// ShaosongMap 纯函数工具库（无 DOM 依赖，可直接单测）

/** HTML 转义，防 XSS（纯字符串实现，无 DOM 依赖） */
var ENTITY_MAP = {'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;', '`': '&#96;'};

/** HTML 转义，防 XSS（纯字符串实现，无 DOM 依赖） */
function escHtml(s) {
  if (s == null) return '';
  return String(s).replace(/[&<>"'`]/g, function(c) { return ENTITY_MAP[c]; });
}

