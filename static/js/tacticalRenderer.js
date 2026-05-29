// ShaosongMap Tactical 纯 Canvas 渲染器
// Tactical 级（几十公里范围）专用：数据驱动视口，单 Canvas 绘制，无 MapLibre 依赖
// 依赖：roughjs（全局 rough）
// TODO: _drawArrow/_drawFlag/_factionColor/_loadBannerImages 后续抽到 renderUtils.js 共享

(function () {
  'use strict';

  // ── THEME 配置 ──
  // TODO: 后续从共享 renderUtils.js 导入
  var THEME = {
    factionSong: '#2b4c7e',
    factionJin: '#8b4513',
    factionUnknown: '#2c2c2c',
    flagSize: 80,
    arrowLineW: 6,
    labelFontSize: 13,
    arrowRoughness: 2,
    paperBg: '#f2e8d5',
    padding: 60,
    circularRadius: 30  // 多点环形分布半径(px)
  };

  // ── 内部状态 ──
  var canvas = null;
  var ctx = null;
  var container = null;
  var dpr = 1;
  var destroyed = false;
  var roughGen = null;
  var roughCanvas = null;

  // 数据
  var geojsonData = null;
  var currentStep = 0;
  var totalSteps = 0;

  // 投影参数
  var _proj = null; // { scaleX, scaleY, offsetX, offsetY } 或 null

  // ── 工具函数 ──
  function _hash32(s) {
    var h = 0;
    for (var i = 0; i < s.length; i++) {
      h = ((h << 5) - h + s.charCodeAt(i)) | 0;
    }
    return h;
  }

  // ── 阵营色 ──
  // TODO: 后续从共享 renderUtils.js 导入
  function _factionColor(faction) {
    if (!faction) return THEME.factionUnknown;
    if (faction.indexOf('宋') >= 0) return THEME.factionSong;
    if (faction.indexOf('金') >= 0) return THEME.factionJin;
    return THEME.factionUnknown;
  }

  // ── 旗帜图标加载 ──
  // TODO: 后续从共享 renderUtils.js 导入
  var bannerImages = {};
  var bannerLoaded = false;

  function _loadBannerImages() {
    var icons = {
      'song': 'assets/icons/banner-song.svg',
      'jin': 'assets/icons/banner-jin.svg',
      'engaging': 'assets/icons/banner-engaging.svg',
      'unknown': 'assets/icons/banner-jin.svg'
    };
    var pending = Object.keys(icons).length;
    Object.keys(icons).forEach(function (key) {
      var img = new Image();
      img.onload = function () {
        bannerImages[key] = img;
        pending--;
        if (pending === 0) { bannerLoaded = true; }
      };
      img.onerror = function () {
        pending--;
        console.warn('[TacticalRenderer] 旗帜图标加载失败: ' + icons[key]);
      };
      img.src = icons[key];
    });
  }

  // ── 1. 收集所有数据点经纬度 ──
  function _collectAllCoords(data) {
    var coords = [];

    // 地名 features
    (data.features || []).forEach(function (f) {
      if (f.lng != null && f.lat != null) coords.push([f.lng, f.lat]);
    });

    // 路线端点
    (data.routes || []).forEach(function (r) {
      if (r.coordinates) {
        r.coordinates.forEach(function (c) {
          if (c && c.length >= 2) coords.push([c[0], c[1]]);
        });
      }
    });

    // 部队 banner features (来自 geojson 中的 unit 相关 features)
    var geojson = data.geojson;
    if (geojson && geojson.features) {
      geojson.features.forEach(function (f) {
        var geom = f.geometry;
        if (!geom || !geom.coordinates) return;
        if (geom.type === 'Point' && geom.coordinates.length >= 2) {
          coords.push([geom.coordinates[0], geom.coordinates[1]]);
        } else if (geom.type === 'LineString') {
          geom.coordinates.forEach(function (c) {
            if (c && c.length >= 2) coords.push([c[0], c[1]]);
          });
        }
      });
    }

    return coords;
  }

  // ── 2. 计算投影参数 ──
  function _computeProjection(coords, cw, ch) {
    if (!coords || coords.length === 0) {
      // 空数据兜底：默认投影到北京附近
      return _computeProjection([[116.4, 39.9]], cw, ch);
    }

    var lngs = coords.map(function (c) { return c[0]; });
    var lats = coords.map(function (c) { return c[1]; });
    var minLng = Math.min.apply(null, lngs);
    var maxLng = Math.max.apply(null, lngs);
    var minLat = Math.min.apply(null, lats);
    var maxLat = Math.max.apply(null, lats);

    var dLng = maxLng - minLng;
    var dLat = maxLat - minLat;

    // 除零兜底：跨度 < 0.001° 时赋予默认 ±0.005°
    var EPS = 0.001;
    if (dLng < EPS && dLat < EPS) {
      return _computeProjection([
        [minLng - 0.005, minLat - 0.005],
        [maxLng + 0.005, maxLat + 0.005]
      ], cw, ch);
    }
    if (dLng < EPS) dLng = EPS;
    if (dLat < EPS) dLat = EPS;

    // 球面近似修正
    var midLatRad = (minLat + maxLat) / 2 * Math.PI / 180;
    var mPerDegLng = 111320 * Math.cos(midLatRad);
    var mPerDegLat = 111320;

    var dxMeters = dLng * mPerDegLng;
    var dyMeters = dLat * mPerDegLat;

    var pad = THEME.padding;
    var drawW = cw - pad * 2;
    var drawH = ch - pad * 2;

    // 等比缩放（保证不变形）
    var scale = Math.min(drawW / dxMeters, drawH / dyMeters);

    // 居中偏移
    var renderW = dxMeters * scale;
    var renderH = dyMeters * scale;
    var offsetX = pad + (drawW - renderW) / 2;
    var offsetY = pad + (drawH - renderH) / 2;

    return {
      minLng: minLng, maxLat: maxLat,
      mPerDegLng: mPerDegLng, mPerDegLat: mPerDegLat,
      scale: scale, offsetX: offsetX, offsetY: offsetY
    };
  }

  // ── 3. 投影函数：经纬度 → Canvas 像素 ──
  function _project(lng, lat) {
    if (!_proj) return { x: 0, y: 0 };
    var x = (lng - _proj.minLng) * _proj.mPerDegLng * _proj.scale + _proj.offsetX;
    var y = (_proj.maxLat - lat) * _proj.mPerDegLat * _proj.scale + _proj.offsetY;
    return { x: x, y: y };
  }

  // ── 4. 环形分布偏移 ──
  function _circularOffset(slot, total) {
    if (total <= 1) return { x: 0, y: 0 };
    var angle = (2 * Math.PI * slot) / total;
    return {
      x: THEME.circularRadius * Math.cos(angle),
      y: THEME.circularRadius * Math.sin(angle)
    };
  }

  // ── 旗帜绘制 ──
  // TODO: 后续从共享 renderUtils.js 导入
  function _drawFlag(px, py, faction, unitName) {
    if (!bannerLoaded) return;
    var fk = 'unknown';
    if (!faction) fk = 'unknown';
    else if (faction.indexOf('宋') >= 0) fk = 'song';
    else if (faction.indexOf('金') >= 0) fk = 'jin';

    var img = bannerImages[fk];
    if (!img) return;
    var s = THEME.flagSize;
    ctx.drawImage(img, px - s / 2, py - s, s, s);

    if (unitName) {
      ctx.save();
      ctx.font = 'bold ' + THEME.labelFontSize + 'px "Noto Serif SC", "SimSun", serif';
      ctx.fillStyle = THEME.factionUnknown;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'top';
      ctx.shadowColor = '#f2e8d5';
      ctx.shadowBlur = 3;
      ctx.fillText(unitName, px, py + 4);
      ctx.restore();
    }
  }

  // ── 燕尾箭头绘制 ──
  // TODO: 后续从共享 renderUtils.js 导入
  function _drawArrow(x1, y1, x2, y2, color, status, arrowSeed) {
    if (typeof rough === 'undefined' || !roughCanvas) return;
    var dx = x2 - x1;
    var dy = y2 - y1;
    var len = Math.hypot(dx, dy);
    if (len < 2) return;
    var angle = Math.atan2(dy, dx);
    var lw = THEME.arrowLineW;
    var col = color || THEME.factionUnknown;
    var seedBase = arrowSeed !== undefined ? arrowSeed : _hash32('ar-' + Math.round(x1 + y1));

    var alpha = 0.85;
    if (status === 'retreating') alpha = 0.5;
    else if (status === 'routing') alpha = 0.3;

    ctx.save();
    ctx.globalAlpha = alpha;

    var forkLength = lw * 4;
    var forkAngle = Math.PI / 5;
    var backAngle = angle + Math.PI;

    var bodyOpts = {
      stroke: col, strokeWidth: lw, seed: seedBase,
      roughness: THEME.arrowRoughness,
      fillWeight: lw / 2, hachureGap: lw * 4,
      preserveVertices: THEME.arrowRoughness < 2
    };

    if (roughGen) {
      roughCanvas.draw(roughGen.linearPath([[x1, y1], [x2, y2]], bodyOpts));
    }

    var headOpts = {
      stroke: col, strokeWidth: lw, seed: seedBase,
      roughness: Math.min(1, THEME.arrowRoughness)
    };
    if (roughGen) {
      var leftEnd = {
        x: x2 + forkLength * Math.cos(backAngle + forkAngle),
        y: y2 + forkLength * Math.sin(backAngle + forkAngle)
      };
      var rightEnd = {
        x: x2 + forkLength * Math.cos(backAngle - forkAngle),
        y: y2 + forkLength * Math.sin(backAngle - forkAngle)
      };
      roughCanvas.draw(roughGen.line(x2, y2, leftEnd.x, leftEnd.y, headOpts));
      roughCanvas.draw(roughGen.line(x2, y2, rightEnd.x, rightEnd.y, headOpts));
    }

    ctx.restore();
  }

  // ── 单 Canvas 渲染管线 ──
  function _render() {
    if (!ctx || !canvas || !geojsonData) return;
    var w = canvas.width / dpr;
    var h = canvas.height / dpr;
    ctx.clearRect(0, 0, w, h);

    // 1. 背景宣纸色
    ctx.fillStyle = THEME.paperBg;
    ctx.fillRect(0, 0, w, h);

    // TODO: 2. 地形装饰（后续实现）

    var data = geojsonData;
    var features = data.features || [];
    var routes = data.routes || [];
    var geojson = data.geojson;

    // 建立地名坐标查找表
    var placeLookup = {};
    features.forEach(function (f) {
      if (f.name && f.lng != null && f.lat != null) {
        placeLookup[f.name] = { lng: f.lng, lat: f.lat };
      }
    });

    // 3. 行军路线
    ctx.strokeStyle = '#8b4513';
    ctx.lineWidth = 2;
    ctx.setLineDash([8, 4]);
    routes.forEach(function (r) {
      if (!r.coordinates || r.coordinates.length < 2) return;
      ctx.beginPath();
      var start = _project(r.coordinates[0][0], r.coordinates[0][1]);
      ctx.moveTo(start.x, start.y);
      for (var i = 1; i < r.coordinates.length; i++) {
        var pt = _project(r.coordinates[i][0], r.coordinates[i][1]);
        ctx.lineTo(pt.x, pt.y);
      }
      ctx.stroke();
    });
    ctx.setLineDash([]);

    // 4. 地名标记
    features.forEach(function (f) {
      if (f.lng == null || f.lat == null) return;
      var pt = _project(f.lng, f.lat);
      var isCity = f.source === 'chgis';
      if (isCity) {
        // 城池：三角标记
        ctx.fillStyle = '#2c2c2c';
        ctx.beginPath();
        ctx.moveTo(pt.x, pt.y - 8);
        ctx.lineTo(pt.x + 7, pt.y + 6);
        ctx.lineTo(pt.x - 7, pt.y + 6);
        ctx.closePath();
        ctx.fill();
      } else {
        // 营寨：圆形标记
        ctx.fillStyle = '#8b4513';
        ctx.beginPath();
        ctx.arc(pt.x, pt.y, 5, 0, Math.PI * 2);
        ctx.fill();
      }
      // 地名标签
      if (f.name) {
        ctx.save();
        ctx.font = '12px "Noto Serif SC", "SimSun", serif';
        ctx.fillStyle = '#2c2c2c';
        ctx.textAlign = 'center';
        ctx.fillText(f.name, pt.x, pt.y + 10);
        ctx.restore();
      }
    });

    // 5. 部队旗帜 + 6. 攻击箭头
    if (geojson && geojson.features) {
      // 按地理坐标分组部队，计算每组总数（用于环形分布）
      var slotGroups = {};
      var unitBanners = [];
      geojson.features.forEach(function (f) {
        var props = f.properties || {};
        if (props._feature_type !== 'unit_banner') return;
        if (totalSteps > 0 && props.step !== undefined && props.step !== currentStep) return;

        var geom = f.geometry;
        if (!geom || !geom.coordinates || geom.coordinates.length < 2) return;
        var lng = geom.coordinates[0];
        var lat = geom.coordinates[1];

        var key = lng.toFixed(4) + ',' + lat.toFixed(4);
        if (!slotGroups[key]) slotGroups[key] = [];
        var item = { lng: lng, lat: lat, props: props, slot: props._slot || 0 };
        slotGroups[key].push(item);
        unitBanners.push(item);
      });

      // 更新每组总数
      Object.keys(slotGroups).forEach(function (key) {
        var group = slotGroups[key];
        group.forEach(function (item) { item.total = group.length; });
      });

      // 建立名字→屏幕坐标的合并查找表（部队名 + 地名）
      var screenLookup = {};
      // 地名
      Object.keys(placeLookup).forEach(function (name) {
        var p = _project(placeLookup[name].lng, placeLookup[name].lat);
        screenLookup[name] = { x: p.x, y: p.y };
      });
      // 部队
      unitBanners.forEach(function (item) {
        var name = item.props.unit_name;
        if (!name) return;
        var pt = _project(item.lng, item.lat);
        var off = _circularOffset(item.slot, item.total);
        screenLookup[name] = { x: pt.x + off.x, y: pt.y + off.y };
      });

      // 绘制部队旗帜
      unitBanners.forEach(function (item) {
        var pt = _project(item.lng, item.lat);
        var off = _circularOffset(item.slot, item.total);
        _drawFlag(pt.x + off.x, pt.y + off.y, item.props.faction, item.props.unit_name);
      });

      // 绘制攻击箭头
      unitBanners.forEach(function (item) {
        var props = item.props;
        var targetName = props.direction_target;
        if (!targetName) return;

        var tgtScreen = screenLookup[targetName];
        if (!tgtScreen) return;

        var pt = _project(item.lng, item.lat);
        var off = _circularOffset(item.slot, item.total);
        var startX = pt.x + off.x;
        var startY = pt.y + off.y;

        var arrowLen = Math.hypot(tgtScreen.x - startX, tgtScreen.y - startY);
        if (arrowLen >= 30) {
          _drawArrow(startX, startY, tgtScreen.x, tgtScreen.y,
            _factionColor(props.faction), props.status,
            _hash32('arrow-' + (props.unit_name || '') + '-' + targetName));
        }
      });
    }

    // 7. 图例（TODO）
  }

  // ── 公开 API ──

  function init(mapWrapEl) {
    if (destroyed) return;
    container = mapWrapEl;
    dpr = Math.min(window.devicePixelRatio || 1, 2);

    if (typeof rough !== 'undefined') {
      roughGen = rough.generator();
    }

    canvas = document.createElement('canvas');
    canvas.id = 'tactical-canvas';
    canvas.style.cssText = 'position:absolute;top:0;left:0;z-index:10;';

    _resizeCanvas();
    container.appendChild(canvas);

    ctx = canvas.getContext('2d');
    ctx.scale(dpr, dpr);

    window.addEventListener('resize', _onResize);
    _loadBannerImages();

    if (typeof rough !== 'undefined') {
      roughCanvas = rough.canvas(canvas);
    }
  }

  function _resizeCanvas() {
    if (!canvas || !container) return;
    var cw = container.clientWidth || container.offsetWidth || 800;
    var ch = container.clientHeight || container.offsetHeight || 600;
    if (ch < 10) ch = 600;

    canvas.style.width = cw + 'px';
    canvas.style.height = ch + 'px';
    canvas.width = Math.min(cw * dpr, 4096);
    canvas.height = Math.min(ch * dpr, 4096);

    if (ctx) {
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.scale(dpr, dpr);
    }
    if (typeof rough !== 'undefined' && canvas) {
      roughCanvas = rough.canvas(canvas);
    }
  }

  function _onResize() {
    if (destroyed) return;
    _resizeCanvas();
    // Resize 后重算投影
    if (geojsonData) {
      var coords = _collectAllCoords(geojsonData);
      var w = canvas.width / dpr;
      var h = canvas.height / dpr;
      _proj = _computeProjection(coords, w, h);
      _render();
    }
  }

  function setData(data) {
    geojsonData = data;
    totalSteps = data.total_steps || data.events ? (data.events || []).length : 0;
    currentStep = totalSteps > 0 ? 1 : 0;  // 有时间轴时默认显示第一步

    var w = canvas.width / dpr;
    var h = canvas.height / dpr;
    var coords = _collectAllCoords(data);
    _proj = _computeProjection(coords, w, h);
    _render();
  }

  function setTimeline(step, total) {
    currentStep = step;
    totalSteps = total;
    _render();
  }

  function destroy() {
    destroyed = true;
    window.removeEventListener('resize', _onResize);
    if (canvas && canvas.parentNode) {
      canvas.parentNode.removeChild(canvas);
    }
    canvas = null;
    ctx = null;
    container = null;
    roughGen = null;
    roughCanvas = null;
    geojsonData = null;
    bannerImages = {};
    bannerLoaded = false;
    _proj = null;
  }

  // ── 暴露到全局 ──
  window.TacticalRenderer = {
    init: init,
    setData: setData,
    setTimeline: setTimeline,
    destroy: destroy
  };
})();
