// ShaosongMap 纯函数工具库（无 DOM 依赖，可直接单测）

/** HTML 转义，防 XSS（纯字符串实现，无 DOM 依赖） */
function escHtml(s) {
  if (typeof s !== 'string') return '';
  return s.replace(/[&<>"']/g, function(m) {
    if (m === '&') return '&amp;';
    if (m === '<') return '&lt;';
    if (m === '>') return '&gt;';
    if (m === '"') return '&quot;';
    return '&#39;';
  });
}

/** 颜色加深：hex 颜色按 factor 比例变暗 */
function _darkenColor(hex, factor) {
  if (typeof hex !== 'string') return '#000000';
  var match = hex.match(/^#?([a-f\d]{3}|[a-f\d]{6})$/i);
  if (!match) return '#000000';
  var h = match[1];
  if (h.length === 3) h = h[0] + h[0] + h[1] + h[1] + h[2] + h[2];
  factor = Math.max(0, Math.min(1, Number(factor) || 0));
  var clamp = function(c) { return Math.max(0, Math.min(255, Math.round(c * (1 - factor)))); };
  var r = parseInt(h.slice(0, 2), 16);
  var g = parseInt(h.slice(2, 4), 16);
  var b = parseInt(h.slice(4, 6), 16);
  return '#' + [clamp(r), clamp(g), clamp(b)].map(function(c) { return c.toString(16).padStart(2, '0'); }).join('');
}

/** 阵营名 → 阵营色映射 */
function _factionColor(faction) {
  if (!faction || typeof faction !== 'string') return '#2c2c2c';
  if (faction.indexOf('宋') >= 0) return '#2b4c7e';
  if (faction.indexOf('金') >= 0) return '#c23b22';
  return '#2c2c2c';
}

/** 计算点集的对角线距离（米），用于确定渲染尺度 */
function _computeDataDiagonal(features) {
  if (!Array.isArray(features) || features.length === 0) return 1000;
  var minLng = Infinity, maxLng = -Infinity;
  var minLat = Infinity, maxLat = -Infinity;
  var hasValid = false;
  features.forEach(function(f) {
    var coords = f && f.geometry && f.geometry.coordinates;
    if (coords && coords.length >= 2 && typeof coords[0] === 'number' && typeof coords[1] === 'number') {
      if (coords[0] < minLng) minLng = coords[0];
      if (coords[0] > maxLng) maxLng = coords[0];
      if (coords[1] < minLat) minLat = coords[1];
      if (coords[1] > maxLat) maxLat = coords[1];
      hasValid = true;
    }
  });
  if (!hasValid) return 1000;
  var midLat = (minLat + maxLat) / 2 * Math.PI / 180;
  var dx = (maxLng - minLng) * 111320 * Math.cos(midLat);
  var dy = (maxLat - minLat) * 111320;
  return Math.sqrt(dx * dx + dy * dy);
}

/** 地形类型 → 地形色（仅 tactical 级渲染） */
function _terrainColorForType(placeType) {
  if (typeof placeType !== 'string') return null;
  var map = {
    mountain: 'rgba(139,119,101,0.12)',
    mountain_pass: 'rgba(139,119,101,0.12)',
    river: 'rgba(100,149,237,0.15)',
    valley: 'rgba(218,195,125,0.12)',
    region: 'rgba(218,195,125,0.12)'
  };
  return map[placeType] || null;
}
