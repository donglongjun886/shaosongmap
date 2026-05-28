// ShaosongMap Canvas 渲染引擎
// 三层 Canvas 架构 + roughjs 手绘风格
// 依赖：roughjs（全局 rough）、utils.js（_darkenColor / _factionColor）

(function () {
  'use strict';

  // ── THEME_CONFIG（基于 Excalidraw 设计 + Qwen-VL analyze_ui 校对） ──
  var THEME = {
    factionSong: '#2b4c7e',
    factionJin: '#8b4513',
    factionUnknown: '#2c2c2c',
    statusEngaging: '#e63946',
    cardWidth: 84,
    cardHeight: 56,
    cardRadius: 12,
    cardColorBarH: 12,
    cardOuterBorder: 3,
    cardInnerBorder: 1,
    cardFill: '#faf6ed',
    cardInk: '#2c2c2c',
    cardFont: 'bold 14px "Noto Serif SC", "SimSun", serif',
    cardShadowOx: 2,
    cardShadowOy: 3,
    cardShadowBlur: 4,
    cardShadowColor: 'rgba(0,0,0,0.25)',
    arrowWidth: 14,
    arrowHeadRatio: 1.5,
    arrowStrokeWidth: 1.5,
    arrowStrokeColor: '#2c2c2c',
    arrowBowing: 1.5,
    arrowRoughness: 1.2,
    pixelSpacing: 64,
    defaultRoughness: 0.8,
    defaultBowing: 0.5,
    maxPhysicalPx: 4096
  };

  // ── 内部状态 ──
  var layers = {};       // {terrain, route, unit} -> Canvas element
  var ctxs = {};         // {terrain, route, unit} -> CanvasRenderingContext2D
  var dpr = 1;
  var map = null;
  var roughGen = null;
  var dirty = { terrain: true, route: true, unit: true };
  var prevZoomBin = -1;
  var rafId = null;
  var destroyed = false;

  // ── 精灵缓存 ──
  var roughCanvas = null; // roughjs 渲染器，每帧直接画箭头（仿 Excalidraw）

  // ── 数据 ──
  var unitFeatures = [];
  var routeFeatures = [];
  var terrainFeatures = [];
  var currentStep = 0;
  var totalSteps = 0;
  var currentScale = 'battle';

  // ── 视口裁剪辅助 ──
  function _isOnScreen(px, py, margin) {
    var w = layers.unit ? parseInt(layers.unit.style.width) : 800;
    var h = layers.unit ? parseInt(layers.unit.style.height) : 600;
    var m = margin || 100;
    return px > -m && px < w + m && py > -m && py < h + m;
  }

  // ── 缩放分档（用于 terrainCanvas 重绘判定） ──
  function _zoomBin(z) {
    return Math.round(z * 2) / 2;
  }

  // ── zoom 连续 lerp ──
  function _lerpZoom(zoom, zMin, zMax, vMin, vMax) {
    var z = Math.max(zMin, Math.min(zMax, zoom));
    var t = (z - zMin) / (zMax - zMin);
    return Math.round(vMin + t * (vMax - vMin));
  }

  // ── smoothstep easing ──
  function _smoothstep(t) {
    return t * t * (3 - 2 * t);
  }

  // ── 阵营色 ──
  function _factionColor(faction) {
    if (!faction) return THEME.factionUnknown;
    if (faction.indexOf('宋') >= 0) return THEME.factionSong;
    if (faction.indexOf('金') >= 0) return THEME.factionJin;
    return THEME.factionUnknown;
  }

  // ── 简单哈希（用于 seed 生成） ──
  function _hash32(s) {
    var h = 0;
    for (var i = 0; i < s.length; i++) {
      h = ((h << 5) - h + s.charCodeAt(i)) | 0;
    }
    return h;
  }

  // ── 加载旗帜图标（SVG → Image → 缓存） ──
  var bannerImages = {}; // factionKey -> HTMLImageElement
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
        if (pending === 0) {
          bannerLoaded = true;
          console.log('[CanvasRenderer] banner icons all loaded');
        }
      };
      img.onerror = function () {
        pending--;
        console.warn('[CanvasRenderer] failed to load banner icon: ' + icons[key]);
      };
      img.src = icons[key];
    });
  }

  // ── 旗帜绘制（render 事件驱动, drawImage 贴图） ──
  function _drawFlag(ctx, px, py, faction, unitName, size, fontSize) {
    if (!bannerLoaded) return;
    var fk = 'unknown';
    if (!faction) fk = 'unknown';
    else if (faction.indexOf('宋') >= 0) fk = 'song';
    else if (faction.indexOf('金') >= 0) fk = 'jin';

    var img = bannerImages[fk];
    if (!img) return;
    var s = size || 48;
    ctx.drawImage(img, px - s / 2, py - s, s, s);

    if (unitName) {
      ctx.save();
      ctx.font = 'bold ' + (fontSize || 13) + 'px "Noto Serif SC", "SimSun", serif';
      ctx.fillStyle = THEME.cardInk;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'top';
      ctx.shadowColor = '#f2e8d5';
      ctx.shadowBlur = 3;
      ctx.fillText(unitName, px, py + 4);
      ctx.restore();
    }
  }

  // ── 箭头绘制（roughjs 每帧直接画，仿 Excalidraw，无缓存） ──
  function _drawArrow(ctx, x1, y1, x2, y2, color, status, lineW) {
    if (typeof rough === 'undefined' || !roughCanvas) return;
    var dx = x2 - x1;
    var dy = y2 - y1;
    var len = Math.hypot(dx, dy);
    if (len < 5) return;
    var angle = Math.atan2(dy, dx);
    var lw = lineW || THEME.arrowWidth;
    var col = color || THEME.factionUnknown;
    var seedBase = _hash32('ar-' + Math.round(x1 + y1));

    var alpha = 0.85;
    if (status === 'retreating') alpha = 0.5;
    else if (status === 'routing') alpha = 0.3;

    ctx.save();
    ctx.globalAlpha = alpha;

    // 极短箭头：简洁线段，不画头部
    if (len < lw * 3) {
      ctx.strokeStyle = col;
      ctx.lineWidth = Math.max(1, lw * 0.5);
      ctx.lineCap = 'round';
      ctx.beginPath();
      ctx.moveTo(x1, y1);
      ctx.lineTo(x2, y2);
      ctx.stroke();
      ctx.restore();
      return;
    }

    // 箭身：roughjs 手绘线段
    var bodyLen = len * 0.65;
    var bodyX = x1 + Math.cos(angle) * bodyLen;
    var bodyY = y1 + Math.sin(angle) * bodyLen;
    roughCanvas.line(x1, y1, bodyX, bodyY, {
      stroke: col, strokeWidth: lw,
      roughness: 0.8, bowing: 1.0, seed: seedBase
    });

    // 箭头头：roughjs 手绘三角
    var headHalfW = Math.min(lw * THEME.arrowHeadRatio / 2, len * 0.15);
    var perpX = -Math.sin(angle);
    var perpY = Math.cos(angle);
    roughCanvas.linearPath([
      [bodyX + perpX * headHalfW, bodyY + perpY * headHalfW],
      [x2, y2],
      [bodyX - perpX * headHalfW, bodyY - perpY * headHalfW]
    ], {
      stroke: col, strokeWidth: Math.max(1, lw * 0.7),
      fill: col, fillStyle: 'solid',
      roughness: 1.0, bowing: 0.8, seed: seedBase + 1
    });

    // 交战发光
    if (status === 'engaging') {
      ctx.shadowColor = THEME.statusEngaging;
      ctx.shadowBlur = 10;
      ctx.strokeStyle = THEME.statusEngaging;
      ctx.lineWidth = lw + 2;
      ctx.beginPath();
      ctx.moveTo(x1, y1);
      ctx.lineTo(x2, y2);
      ctx.stroke();
    }

    ctx.restore();
  }

  // ── 兵牌层渲染（unitCanvas, render 事件驱动） ──
  function _renderUnitLayer() {
    var ctx = ctxs.unit;
    var canvas = layers.unit;
    if (!ctx || !canvas) return;
    var w = parseInt(canvas.style.width);
    var h = parseInt(canvas.style.height);
    ctx.clearRect(0, 0, w, h);

    if (!unitFeatures.length) return;

    var zoom = map.getZoom();
    var now = performance.now();
    var cZoom = Math.max(6, Math.min(14, zoom));
    var flagSize = _lerpZoom(zoom, 6, 14, 48, 80);
    var arrowBaseLen = _lerpZoom(zoom, 6, 14, 90, 200);
    var arrowLineW = _lerpZoom(zoom, 6, 14, 6, 14);
    var labelFontSize = _lerpZoom(zoom, 6, 14, 11, 13);

    unitFeatures.forEach(function (f) {
      if (totalSteps > 0) {
        var step = f.properties && f.properties.step;
        if (step !== undefined && step !== currentStep) return;
      }
      if (currentScale !== 'tactical' && currentScale !== 'battle') return;

      var coords = f.geometry && f.geometry.coordinates;
      if (!coords || coords.length < 2) return;

      var pt = map.project(coords);
      if (!pt || isNaN(pt.x) || isNaN(pt.y)) return;
      if (!_isOnScreen(pt.x, pt.y, 200)) return;

      var props = f.properties || {};
      var slot = props._slot || 0;
      if (slot > 0) pt.y += slot * THEME.pixelSpacing;

      // 碰撞偏移 smoothstep 动画
      var targetOff = f._targetOffsetY !== undefined ? f._targetOffsetY : 0;
      if (f._animStartTime !== undefined) {
        var dt = Math.min(now - f._animStartTime, 50); // deltaTime 上限防切后台跳跃
        if (dt >= 180) {
          f._currentOffsetY = targetOff;
        } else {
          var t = _smoothstep(dt / 180);
          f._currentOffsetY = f._animStartY + (targetOff - f._animStartY) * t;
        }
      } else {
        f._currentOffsetY = targetOff;
      }

      var drawY = pt.y + (f._currentOffsetY || 0);

      var faction = props.faction || '';
      var unitName = props.unit_name || '';
      var status = props.status || '';

      _drawFlag(ctx, pt.x, drawY, faction, unitName, flagSize, labelFontSize);

      if (props.direction && props.direction !== '未明确') {
        var dirAngle = _directionAngle(props.direction);
        if (dirAngle !== null) {
          var arrowLen = arrowBaseLen;
          var endX = pt.x + Math.cos(dirAngle) * arrowLen;
          var endY = drawY - flagSize / 2 - Math.sin(dirAngle) * arrowLen;
          _drawArrow(ctx, pt.x, drawY - flagSize / 2, endX, endY, _factionColor(faction), status, arrowLineW);
        }
      }
    });
  }

  // ── 方向→角度映射 ──
  function _directionAngle(dir) {
    var d = (dir || '').replace(/偏[东西南北]/g, '');
    var angles = { '北': Math.PI / 2, '南': -Math.PI / 2, '东': 0, '西': Math.PI,
                   '东北': Math.PI / 4, '东南': -Math.PI / 4, '西北': 3 * Math.PI / 4, '西南': -3 * Math.PI / 4 };
    return angles[d] !== undefined ? angles[d] : null;
  }

  // ── 路线层渲染（routeCanvas, 步骤切换时重绘） ──
  function _renderRouteLayer() {
    var ctx = ctxs.route;
    var canvas = layers.route;
    if (!ctx || !canvas) return;
    var w = parseInt(canvas.style.width);
    var h = parseInt(canvas.style.height);
    ctx.clearRect(0, 0, w, h);
    // 路线由 MapLibre line/symbol layer 渲染，routeCanvas 暂用于额外标注
    // P0: 保持 MapLibre 路线渲染不变，后续可搬到此层
    dirty.route = false;
  }

  // ── 地形层渲染（terrainCanvas, zoom 跨 0.5 档时重绘） ──
  function _renderTerrainLayer() {
    var ctx = ctxs.terrain;
    var canvas = layers.terrain;
    if (!ctx || !canvas) return;
    var w = parseInt(canvas.style.width);
    var h = parseInt(canvas.style.height);
    ctx.clearRect(0, 0, w, h);
    // P0: 地形渲染在 terrainRenderer.js 中实现
    // 此处调用 terrainRenderer.render(ctx, terrainFeatures, map) 占位
    if (window.TerrainRenderer && window.TerrainRenderer.render) {
      window.TerrainRenderer.render(ctx, terrainFeatures, map);
    }
    dirty.terrain = false;
  }

  // ── 渲染循环（MapLibre render 事件驱动，替代独立 rAF） ──
  var _lastFrameTime = 0;

  function _onMapRender() {
    if (!map || destroyed) return;
    // 与 MapLibre 同帧渲染，不额外节流
    _renderUnitLayer();
    dirty.unit = false;
  }

  function _onMapIdle() {
    if (!map || destroyed) return;
    _recalcOffsets();
  }

  // ── 碰撞避让（idle 时计算 targetOffsetY） ──
  function _recalcOffsets() {
    if (!unitFeatures.length) return;
    var placeBounds = typeof getPlaceBounds === 'function' ? getPlaceBounds() : [];
    var screenH = layers.unit ? parseInt(layers.unit.style.height) : 600;
    if (!screenH || screenH < 10) screenH = 600;
    var zoom = map.getZoom();
    var flagSize = _lerpZoom(zoom, 6, 14, 48, 80);
    var stepPx = flagSize + 4;
    var drawnRects = []; // 重置每轮碰撞计算
    var now = performance.now();

    // 按优先级排序：engaging > marching > deploying > retreating > routing
    var sorted = unitFeatures.slice().sort(function (a, b) {
      var order = { engaging: 0, marching: 1, deploying: 2, retreating: 3, routing: 4 };
      var sa = order[(a.properties && a.properties.status) || 'marching'] || 2;
      var sb = order[(b.properties && b.properties.status) || 'marching'] || 2;
      return sa - sb;
    });

    sorted.forEach(function (f) {
      if (totalSteps > 0) {
        var step = f.properties && f.properties.step;
        if (step !== undefined && step !== currentStep) return;
      }
      var coords = f.geometry && f.geometry.coordinates;
      if (!coords || coords.length < 2) return;

      var pt = map.project(coords);
      if (!pt || isNaN(pt.x) || isNaN(pt.y)) return;

      var origY = pt.y;
      var direction = -1; // 向北优先
      var offset = 0;
      var bestY = origY;

      for (var attempt = 0; attempt < 3; attempt++) {
        var tryY = origY + offset * direction;
        var fRect = { x: pt.x - flagSize / 2, y: tryY - flagSize, w: flagSize, h: flagSize };

        var collides = false;
        for (var i = 0; i < placeBounds.length; i++) {
          if (_aabbOverlap(fRect, placeBounds[i])) { collides = true; break; }
        }
        if (!collides) {
          for (var j = 0; j < drawnRects.length; j++) {
            if (_aabbOverlap(fRect, drawnRects[j])) { collides = true; break; }
          }
        }

        if (!collides) { bestY = tryY; break; }

        offset += stepPx;
        if (tryY - flagSize < 0 && direction === -1) {
          direction = 1;
          offset = stepPx;
          continue;
        }
        if (tryY + flagSize > screenH && direction === 1) {
          offset = 0;
          bestY = origY;
          break;
        }
      }

      drawnRects.push({ x: pt.x - flagSize / 2, y: bestY - flagSize, w: flagSize, h: flagSize });

      // 动画过渡
      var prevOffset = f._currentOffsetY !== undefined ? f._currentOffsetY : 0;
      f._targetOffsetY = bestY - origY;
      f._animStartY = prevOffset;
      f._animStartTime = now;
    });
  }

  function _aabbOverlap(a, b) {
    return !(a.x + a.w < b.x || b.x + b.w < a.x || a.y + a.h < b.y || b.y + b.h < a.y);
  }

  // ── MapLibre 事件处理 ──
  function _onResize() {
    var container = map.getCanvasContainer();
    var cw = container.clientWidth || container.offsetWidth || 800;
    var ch = container.clientHeight || container.offsetHeight || 600;
    // 防止 MapLibre 动画期间出现零高度
    if (ch < 10) return; // 忽略无效 resize
    dpr = Math.min(window.devicePixelRatio || 1, 2);
    var pw = Math.min(cw * dpr, THEME.maxPhysicalPx);
    var ph = Math.min(ch * dpr, THEME.maxPhysicalPx);

    ['terrain', 'route', 'unit'].forEach(function (name) {
      var canvas = layers[name];
      if (!canvas) return;
      // 仅在尺寸确实变化时更新
      if (canvas.style.width === cw + 'px' && canvas.style.height === ch + 'px') return;
      canvas.style.width = cw + 'px';
      canvas.style.height = ch + 'px';
      canvas.width = pw;
      canvas.height = ph;
      var ctx = canvas.getContext('2d');
      ctx.scale(dpr, dpr);
      ctxs[name] = ctx;
      if (name === 'unit' && typeof rough !== 'undefined') {
        roughCanvas = rough.canvas(canvas);
      }
    });
    dirty.terrain = true;
    dirty.route = true;
    dirty.unit = true;
  }

  // ── 初始化 ──
  function init(mapInstance) {
    if (destroyed) return;
    map = mapInstance;
    dpr = Math.min(window.devicePixelRatio || 1, 2);

    if (typeof rough !== 'undefined') {
      roughGen = rough.generator({ options: { roughness: THEME.defaultRoughness, bowing: THEME.defaultBowing } });
    }

    var container = map.getCanvasContainer();
    // 确保容器有正确高度（MapLibre 加载后可能为 0）
    var cw = container.clientWidth || container.offsetWidth || 800;
    var ch = container.clientHeight || container.offsetHeight || 600;
    if (ch < 10) ch = container.parentElement ? container.parentElement.clientHeight : 600;
    if (ch < 10) ch = 600;

    var pw = Math.min(cw * dpr, THEME.maxPhysicalPx);
    var ph = Math.min(ch * dpr, THEME.maxPhysicalPx);

    var zMap = { terrain: '10', route: '20', unit: '30' };

    ['terrain', 'route', 'unit'].forEach(function (name) {
      var canvas = document.createElement('canvas');
      canvas.id = name + '-canvas';
      canvas.style.cssText = 'position:absolute;top:0;left:0;pointer-events:none;z-index:' + zMap[name] + ';';
      canvas.style.width = cw + 'px';
      canvas.style.height = ch + 'px';
      canvas.width = pw;
      canvas.height = ph;
      container.appendChild(canvas);
      layers[name] = canvas;
      var ctx = canvas.getContext('2d');
      ctx.scale(dpr, dpr);
      ctxs[name] = ctx;
    });

    map.on('render', _onMapRender);
    map.on('idle', _onMapIdle);
    map.on('resize', _onResize);

    prevZoomBin = _zoomBin(map.getZoom());

    _loadBannerImages();

    if (typeof rough !== 'undefined') {
      roughCanvas = rough.canvas(layers.unit);
    }

    dirty.terrain = true;
    dirty.route = true;
    dirty.unit = true;
  }

  // ── 公开 API ──
  function setData(unitBannerFeatures, unitDirectionFeatures, terrainFeats, scale) {
    unitFeatures = unitBannerFeatures || [];
    // 合并方向信息
    if (unitDirectionFeatures && unitDirectionFeatures.length) {
      var dirMap = {};
      unitDirectionFeatures.forEach(function (f) {
        var props = f.properties || {};
        var key = (props.unit_name || '') + '@' + (props.step || 0);
        dirMap[key] = props.direction;
      });
      unitFeatures.forEach(function (f) {
        var props = f.properties || {};
        var key = (props.unit_name || '') + '@' + (props.step || 0);
        if (dirMap[key]) props.direction = dirMap[key];
      });
    }
    terrainFeatures = terrainFeats || [];
    currentScale = scale || 'battle';
    dirty.unit = true;
    dirty.route = true;
    dirty.terrain = true;
  }

  function setTimeline(step, total) {
    currentStep = step;
    totalSteps = total;
    dirty.unit = true;
    dirty.route = true;
  }

  function markDirty(layerName) {
    if (dirty.hasOwnProperty(layerName)) {
      dirty[layerName] = true;
    }
  }

  function resize() {
    _onResize();
  }

  function destroy() {
    destroyed = true;
    if (rafId) cancelAnimationFrame(rafId);
    clearTimeout(zoomDebounceTimer);
    if (map) {
      map.off('render', _onMapRender);
      map.off('idle', _onMapIdle);
      map.off('resize', _onResize);
    }
    // 移除 Canvas 元素
    ['terrain', 'route', 'unit'].forEach(function (name) {
      var canvas = layers[name];
      if (canvas && canvas.parentNode) canvas.parentNode.removeChild(canvas);
      delete layers[name];
      delete ctxs[name];
    });
    bannerImages = {};
    bannerLoaded = false;
    roughCanvas = null;
    roughGen = null;
  }

  // ── 暴露到全局 ──
  window.CanvasRenderer = {
    init: init,
    setData: setData,
    setTimeline: setTimeline,
    markDirty: markDirty,
    resize: resize,
    destroy: destroy,
    THEME: THEME
  };
})();
