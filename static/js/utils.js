// ShaosongMap 纯函数工具库（无 DOM 依赖，可直接单测）

/** HTML 转义，防 XSS */
function escHtml(s) {
  var d = document.createElement('div');
  d.textContent = s;
  return d.innerHTML;
}

/** 颜色加深：hex 颜色按 factor 比例变暗 */
function _darkenColor(hex, factor) {
  var r = parseInt(hex.slice(1, 3), 16);
  var g = parseInt(hex.slice(3, 5), 16);
  var b = parseInt(hex.slice(5, 7), 16);
  var dr = Math.round(r * (1 - factor));
  var dg = Math.round(g * (1 - factor));
  var db = Math.round(b * (1 - factor));
  return '#' + [dr, dg, db].map(function(c) { return c.toString(16).padStart(2, '0'); }).join('');
}

/** 阵营名 → 阵营色映射 */
function _factionColor(faction) {
  if (!faction) return '#2c2c2c';
  if (faction.indexOf('宋') >= 0) return '#2b4c7e';
  if (faction.indexOf('金') >= 0) return '#c23b22';
  return '#2c2c2c';
}

/** 计算点集的对角线距离（米），用于确定渲染尺度 */
function _computeDataDiagonal(features) {
  var lngs = [], lats = [];
  features.forEach(function(f) {
    if (f.geometry && f.geometry.coordinates) {
      lngs.push(f.geometry.coordinates[0]);
      lats.push(f.geometry.coordinates[1]);
    }
  });
  if (lngs.length < 2) return 1000;
  var minLng = Math.min.apply(null, lngs), maxLng = Math.max.apply(null, lngs);
  var minLat = Math.min.apply(null, lats), maxLat = Math.max.apply(null, lats);
  var midLat = (minLat + maxLat) / 2 * Math.PI / 180;
  var dx = (maxLng - minLng) * 111320 * Math.cos(midLat);
  var dy = (maxLat - minLat) * 111320;
  return Math.sqrt(dx * dx + dy * dy);
}

/** 地形类型 → 地形色（仅 tactical 级渲染） */
function _terrainColorForType(placeType) {
  var map = {
    mountain: 'rgba(139,119,101,0.12)',
    mountain_pass: 'rgba(139,119,101,0.12)',
    river: 'rgba(100,149,237,0.15)',
    valley: 'rgba(218,195,125,0.12)',
    region: 'rgba(218,195,125,0.12)',
  };
  return map[placeType] || null;
}