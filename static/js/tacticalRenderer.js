// ShaosongMap Tactical 纯 Canvas 渲染器
// Tactical 级（几十公里范围）专用：数据驱动视口，单 Canvas 绘制，无 MapLibre 依赖
// 依赖：roughjs（全局 rough）
// TODO: _drawArrow/_drawUnitCard/_factionColor 后续抽到 renderUtils.js 共享

(function () {
  'use strict';

  // ── THEME 配置 ──
  // TODO: 后续从共享 renderUtils.js 导入
  var THEME = {
    factionSong: '#d31721',
    factionJin: '#3d588f',
    factionUnknown: '#2c2c2c',
    arrowLineW: 5,
    arrowRoughness: 1.8,
    arrowForkMult: 3.5,    // 分叉长度 = 线宽 × 此值
    arrowForkAngleDeg: 22,  // 分叉张开角度
    paperBg: '#f2e8d5',
    padding: 60,
    circularRadius: 45,
    // 兵牌手绘卡片参数
    cardW: 80,
    cardH: 32,
    cardColorBarW: 11,
    cardRoughness: 1.4,
    cardFont: 'bold 12px "Noto Serif SC", "SimSun", serif',
    cardSubFont: '10px "Noto Serif SC", "SimSun", serif',
    // 地点标记参数
    placeTriSize: 11,
    placeDotRadius: 7,
    placeLabelFont: '15px "Noto Serif SC", "SimSun", serif',
    // 地形渲染参数
    terrainRoughness: 2.2,
    terrainAlpha: 0.25,
    terrainFillWeight: 1.2,
    terrainHachureGap: 6,
    terrainSizeRatio: 0.60,  // 色块半径 = 数据对角线 × 此比例
    terrainBase: { fillStyle: 'hachure', color: '#c8b896', alpha: 0.08, angle: 0 },
    terrainTypes: {
      mountain:      { fillStyle: 'cross-hatch', color: '#8b7765', angle: -45 },
      mountain_pass: { fillStyle: 'hachure',     color: '#9b8765', angle: -30 },
      river:         { fillStyle: 'zigzag',      color: '#6495ed', angle:  0  },
      battlefield:   { fillStyle: 'dashed',      color: '#c23b22', angle:  45 },
      camp:          { fillStyle: 'solid',       color: '#b8a080', angle:  0  }
    }
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

  // ── 数据对角线计算（用于地形尺寸） ──

  function _computeDataDiagonal(features) {
    if (!features || features.length < 2) return 100;
    var lngs = [], lats = [];
    features.forEach(function (f) {
      if (f.lng != null && f.lat != null) { lngs.push(f.lng); lats.push(f.lat); }
    });
    if (lngs.length < 2) return 100;
    var minLng = Math.min.apply(null, lngs), maxLng = Math.max.apply(null, lngs);
    var minLat = Math.min.apply(null, lats), maxLat = Math.max.apply(null, lats);
    var midLatRad = (minLat + maxLat) / 2 * Math.PI / 180;
    var dx = (maxLng - minLng) * 111320 * Math.cos(midLatRad);
    var dy = (maxLat - minLat) * 111320;
    return Math.sqrt(dx * dx + dy * dy);
  }

  // ── 地形色块绘制 ──

  // 生成不规则多边形顶点（基于椭圆 + 随机扰动）
  function _irregularVerts(cx, cy, w, h, seed) {
    var verts = [];
    var N = 12;
    for (var i = 0; i < N; i++) {
      var angle = (2 * Math.PI * i) / N;
      var rnd = ((seed * (i + 1) * 31 + i * 17) % 100) / 100;
      var jitter = 0.7 + rnd * 0.6;
      var rx = (w / 2) * jitter;
      var ry = (h / 2) * jitter;
      verts.push([cx + rx * Math.cos(angle), cy + ry * Math.sin(angle)]);
    }
    return verts;
  }

  // 绘制单块地形色块
  function _drawTerrainBlock(px, py, sizeMeters, placeType) {
    if (!roughGen || !roughCanvas) return;
    // 底图层：使用 terrainBase 配置
    var cfg, blockPx, blockPy, colorAlpha;
    if (placeType._base) {
      cfg = THEME.terrainBase;
      blockPx = sizeMeters;  // 底图层直接传像素尺寸
      blockPy = sizeMeters * 0.7;
      colorAlpha = cfg.alpha;
    } else {
      cfg = THEME.terrainTypes[placeType];
      if (!cfg) return;
      // 米 → 像素（用投影中的 scale）
      blockPx = sizeMeters * (_proj ? _proj.scale : 1);
      blockPx = Math.min(Math.max(blockPx, 30), 800); // 钳制 30~800px
      blockPy = blockPx * 0.7;
      colorAlpha = THEME.terrainAlpha;
    }

    var seed = _hash32('terrain-' + px + '-' + py);
    var verts = _irregularVerts(px, py, blockPx, blockPy, seed);

    var col = cfg.color;
    var r = parseInt(col.slice(1, 3), 16);
    var g = parseInt(col.slice(3, 5), 16);
    var b = parseInt(col.slice(5, 7), 16);
    var fillColor = 'rgba(' + r + ',' + g + ',' + b + ',' + colorAlpha + ')';

    var opts = {
      fill: fillColor,
      fillStyle: cfg.fillStyle,
      roughness: THEME.terrainRoughness,
      fillWeight: THEME.terrainFillWeight,
      hachureGap: THEME.terrainHachureGap,
      hachureAngle: cfg.angle || 0,
      stroke: 'transparent',
      seed: seed
    };
    roughCanvas.draw(roughGen.polygon(verts, opts));
  }

  // ── 部队兵牌绘制（roughjs 手绘矩形卡片，替代 SVG 图标） ──
  function _drawUnitCard(px, py, faction, unitName, troopCount) {
    if (!roughGen || !roughCanvas) return;
    var col = _factionColor(faction);
    var cw = THEME.cardW;
    var ch = THEME.cardH;
    var bw = THEME.cardColorBarW;
    var seed = _hash32('card-' + (unitName || 'x'));

    var left = px - cw / 2;
    var top = py - ch;

    // 卡片背景（米白底矩形）
    var bodyOpts = {
      fill: '#faf6ed', stroke: col, strokeWidth: 1.5,
      fillStyle: 'solid', seed: seed,
      roughness: THEME.cardRoughness
    };
    roughCanvas.draw(roughGen.rectangle(left, top, cw, ch, bodyOpts));

    // 左侧阵营色条（左移2px覆盖卡片左边框，避免视觉加粗）
    var barOpts = { fill: col, fillStyle: 'solid', roughness: 0.5, seed: seed + 1 };
    roughCanvas.draw(roughGen.rectangle(left - 2, top, bw + 2, ch, barOpts));

    // 文字在色条右侧区域内上下左右居中
    var textX = left + bw + (cw - bw) / 2;
    if (unitName) {
      ctx.save();
      ctx.font = THEME.cardFont;
      ctx.fillStyle = THEME.factionUnknown;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(unitName, textX, top + ch / 2 - 4);
      ctx.restore();
    }

    // 兵数（名称下方小字）
    if (troopCount) {
      ctx.save();
      ctx.font = THEME.cardSubFont;
      ctx.fillStyle = '#666';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(troopCount, textX, top + ch / 2 + 10);
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

    var forkLength = lw * THEME.arrowForkMult;
    var forkAngle = THEME.arrowForkAngleDeg * Math.PI / 180;
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

    var data = geojsonData;
    var features = data.features || [];
    var geojson = data.geojson;

    // 2. 地形色块
    // 底图层：全画布中性土色，填充各地形色块间隙
    _drawTerrainBlock(w / 2, h / 2, Math.max(w, h), { _base: true });
    // 各地形色块叠加
    var diagonalM = _computeDataDiagonal(features);
    var terrainSizeM = diagonalM * THEME.terrainSizeRatio;
    features.forEach(function (f) {
      if (f.lng == null || f.lat == null || !f.place_type) return;
      var pt = _project(f.lng, f.lat);
      _drawTerrainBlock(pt.x, pt.y, terrainSizeM, f.place_type);
    });

    // 非时间轴模式：暂不支持
    if (totalSteps === 0) {
      ctx.save();
      ctx.font = '20px "Noto Serif SC", "SimSun", serif';
      ctx.fillStyle = '#999';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText('暂不支持非时间轴模式，请勾选「时间轴模式」后重试', w / 2, h / 2);
      ctx.restore();
      return;
    }

    // 建立地名坐标查找表
    var placeLookup = {};
    features.forEach(function (f) {
      if (f.name && f.lng != null && f.lat != null) {
        placeLookup[f.name] = { lng: f.lng, lat: f.lat };
      }
    });

    // 3. 地名标记
    features.forEach(function (f) {
      if (f.lng == null || f.lat == null) return;
      var pt = _project(f.lng, f.lat);
      var isCity = f.source === 'chgis';
      if (isCity) {
        // 城池：三角标记
        var ts = THEME.placeTriSize;
        ctx.fillStyle = '#2c2c2c';
        ctx.beginPath();
        ctx.moveTo(pt.x, pt.y - ts);
        ctx.lineTo(pt.x + ts - 1, pt.y + ts - 2);
        ctx.lineTo(pt.x - ts + 1, pt.y + ts - 2);
        ctx.closePath();
        ctx.fill();
      } else {
        // 营寨：圆形标记
        ctx.fillStyle = '#8b4513';
        ctx.beginPath();
        ctx.arc(pt.x, pt.y, THEME.placeDotRadius, 0, Math.PI * 2);
        ctx.fill();
      }
      // 地名标签
      if (f.name) {
        ctx.save();
        ctx.font = THEME.placeLabelFont;
        ctx.fillStyle = '#2c2c2c';
        ctx.textAlign = 'center';
        ctx.fillText(f.name, pt.x, pt.y + 10);
        ctx.restore();
      }
    });

    // 4. 部队兵牌 + 5. 攻击箭头
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
        var item = { lng: lng, lat: lat, props: props, slot: slotGroups[key].length };
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

      // 部队编制→兵数查找表
      var troopLookup = {};
      (data.units || []).forEach(function (u) {
        if (u.name) troopLookup[u.name] = u.troop_count || '';
      });

      // 绘制部队兵牌
      unitBanners.forEach(function (item) {
        var pt = _project(item.lng, item.lat);
        var off = _circularOffset(item.slot, item.total);
        _drawUnitCard(pt.x + off.x, pt.y + off.y, item.props.faction,
          item.props.unit_name, troopLookup[item.props.unit_name] || '');
      });

      // 5. 攻击箭头
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

    // 6. 图例（TODO）
  }

  // ── 公开 API ──

  function init(mapWrapEl) {
    destroyed = false;
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
    if (!canvas) { console.warn('[TacticalRenderer] setData 在 init 之前调用，跳过'); return; }
    geojsonData = data;
    totalSteps = data.total_steps || data.events ? (data.events || []).length : 0;
    currentStep = totalSteps > 0 ? 1 : 0;

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
