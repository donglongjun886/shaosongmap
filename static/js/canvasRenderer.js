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
    arrowWidth: 4,
    arrowHeadRatio: 8,
    arrowStrokeWidth: 1.5,
    arrowStrokeColor: '#2c2c2c',
    arrowBowing: 0,
    arrowRoughness: 2,
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
  var destroyed = false;

  // ── 精灵缓存 ──
  var roughCanvas = null; // roughjs 渲染器，每帧直接画箭头（仿 Excalidraw）

  // ── 数据 ──
  var unitFeatures = [];
  var routeFeatures = [];
  var terrainFeatures = [];
  var targetLookup = {};  // name → {x, y} 屏幕坐标缓存（O(1)箭头终点查询）
  var currentStep = 0;
  var totalSteps = 0;
  var currentScale = 'battle';

  // ── 线段截断到屏幕边缘 ──
  function _clipToScreen(x1, y1, x2, y2) {
    var cw = layers.unit ? parseInt(layers.unit.style.width) : 800;
    var ch = layers.unit ? parseInt(layers.unit.style.height) : 600;
    var dx = x2 - x1, dy = y2 - y1;
    var tMax = 1;
    if (dx > 0) tMax = Math.min(tMax, (cw - 20 - x1) / dx);
    else if (dx < 0) tMax = Math.min(tMax, (20 - x1) / dx);
    if (dy > 0) tMax = Math.min(tMax, (ch - 20 - y1) / dy);
    else if (dy < 0) tMax = Math.min(tMax, (20 - y1) / dy);
    if (tMax < 0 || tMax > 1) return null;
    return { x: x1 + dx * tMax, y: y1 + dy * tMax };
  }

  // ── 视口范围检测 ──
  function _isOnScreen(px, py, margin) {
    var w = layers.unit ? parseInt(layers.unit.style.width) : 800;
    var h = layers.unit ? parseInt(layers.unit.style.height) : 600;
    var m = margin || 100;
    return px > -m && px < w + m && py > -m && py < h + m;
  }

  // ── smoothstep easing ──
  function _smoothstep(t) {
    return t * t * (3 - 2 * t);
  }

  // ── scale 参数查表（替代 zoom lerp） ──
  function _scaleParams(scale) {
    switch (scale) {
      case 'tactical':  return { flagSize: 80, arrowLineW: 6, labelFontSize: 13 };
      case 'battle':    return { flagSize: 64, arrowLineW: 4, labelFontSize: 12 };
      case 'strategic': return { flagSize: 48, arrowLineW: 3, labelFontSize: 11 };
      default:          return { flagSize: 64, arrowLineW: 4, labelFontSize: 12 };
    }
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
  function _drawArrow(ctx, x1, y1, x2, y2, color, status, lineW, arrowSeed) {
    if (typeof rough === 'undefined' || !roughCanvas) return;
    var dx = x2 - x1;
    var dy = y2 - y1;
    var len = Math.hypot(dx, dy);
    if (len < 2) return;
    var angle = Math.atan2(dy, dx);
    var lw = lineW || THEME.arrowWidth;
    var col = color || THEME.factionUnknown;
    var seedBase = arrowSeed !== undefined ? arrowSeed : _hash32('ar-' + Math.round(x1 + y1));

    var alpha = 0.85;
    if (status === 'retreating') alpha = 0.5;
    else if (status === 'routing') alpha = 0.3;

    ctx.save();
    ctx.globalAlpha = alpha;

    // 燕尾分叉几何：箭身直达终点，分叉向后张开
    var forkLength = lw * 4;
    var forkAngle = Math.PI / 5;  // 36° 张开角
    var backAngle = angle + Math.PI;

    // 箭身选项
    var bodyOpts = {
      stroke: col, strokeWidth: lw, seed: seedBase,
      roughness: THEME.arrowRoughness,
      fillWeight: lw / 2, hachureGap: lw * 4,
      preserveVertices: THEME.arrowRoughness < 2
    };

    // 箭身：直达终点（燕尾式，body 贯穿到 to）
    if (roughGen) {
      roughCanvas.draw(roughGen.linearPath([[x1, y1], [x2, y2]], bodyOpts));
    }

    // 燕尾分叉：从终点向后张开两条线
    var headOpts = {
      stroke: col, strokeWidth: lw, seed: seedBase,
      roughness: Math.min(1, THEME.arrowRoughness)
    };
    if (roughGen) {
      var leftEnd = { x: x2 + forkLength * Math.cos(backAngle + forkAngle), y: y2 + forkLength * Math.sin(backAngle + forkAngle) };
      var rightEnd = { x: x2 + forkLength * Math.cos(backAngle - forkAngle), y: y2 + forkLength * Math.sin(backAngle - forkAngle) };
      roughCanvas.draw(roughGen.line(x2, y2, leftEnd.x, leftEnd.y, headOpts));
      roughCanvas.draw(roughGen.line(x2, y2, rightEnd.x, rightEnd.y, headOpts));
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

    var now = performance.now();
    var sp = _scaleParams(currentScale);
    var flagSize = sp.flagSize;
    var arrowLineW = sp.arrowLineW;
    var labelFontSize = sp.labelFontSize;

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

      // 箭头：direction_target 指向目标地点/部队
      var targetName = props.direction_target;
      if (targetName && targetLookup[targetName]) {
        var tgt = targetLookup[targetName];
        var endPt = map.project([tgt.lng, tgt.lat]);
        if (endPt && isFinite(endPt.x) && isFinite(endPt.y)) {
          // 方向：从部队原始地理坐标（slot偏移前）指向目标
          var dir = Math.atan2(endPt.y - pt.y, endPt.x - pt.x);
          // 起点沿箭头方向前移，脱离地点图标（128 / 2dpr * 0.78 ≈ 50px，半高 25px）
          var startX = pt.x + 0 * Math.cos(dir);
          var startY = pt.y + 0 * Math.sin(dir);
          // 终点回退，避免燕尾覆盖目标地名图标
          var headMargin = flagSize * 0.5 + arrowLineW * 4;
          var endX = endPt.x - headMargin * Math.cos(dir);
          var endY = endPt.y - headMargin * Math.sin(dir);
          var arrowLen = Math.hypot(endX - startX, endY - startY);
          console.log('[arrow]', unitName, '| geoPt:', pt.x.toFixed(1)+','+pt.y.toFixed(1),
            '| flagSize:', flagSize, '| drawY:', drawY.toFixed(1),
            '| tail:', startX.toFixed(1)+','+startY.toFixed(1),
            '| head:', endX.toFixed(1)+','+endY.toFixed(1),
            '| tgtPt:', endPt.x.toFixed(1)+','+endPt.y.toFixed(1),
            '| len:', arrowLen.toFixed(1));
          if (arrowLen >= 30) {
            if (!_isOnScreen(endX, endY, 0)) {
              var clip = _clipToScreen(startX, startY, endX, endY);
              if (clip) { endX = clip.x; endY = clip.y; }
            }
            _drawArrow(ctx, startX, startY, endX, endY, _factionColor(faction), status, arrowLineW, props._arrowSeed);
          }
        }
      }
    });
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
  }

  // ── 地形层渲染（缓存到离屏 Canvas，避免 roughjs 重复计算） ──
  function _renderTerrainLayer() {
    var ctx = ctxs.terrain;
    var canvas = layers.terrain;
    if (!ctx || !canvas) return;
    var w = parseInt(canvas.style.width);
    var h = parseInt(canvas.style.height);
    ctx.clearRect(0, 0, w, h);

    if (!_terrainCache || _terrainCache.width !== w || _terrainCache.height !== h) {
      _terrainCache = document.createElement('canvas');
      _terrainCache.width = canvas.width;
      _terrainCache.height = canvas.height;
      var cacheCtx = _terrainCache.getContext('2d');
      cacheCtx.scale(dpr, dpr);
      if (window.TerrainRenderer && window.TerrainRenderer.render) {
        window.TerrainRenderer.render(cacheCtx, terrainFeatures, map, currentScale);
      }
    }
    ctx.drawImage(_terrainCache, 0, 0);
  }

  // ── 渲染循环（事件驱动，非每帧 rAF） ──
  var _needsRender = false;
  var _terrainCache = null;
  var _resizeDebounceTimer = null;

  function _renderAll() {
    _renderTerrainLayer();
    _renderRouteLayer();
    _renderUnitLayer();
    _needsRender = false;
  }

  function _renderRouteAndUnit() {
    _renderRouteLayer();
    _renderUnitLayer();
  }

  function _onMapIdle() {
    if (!map || destroyed) return;
    if (_needsRender) {
      _recalcOffsets();
      _renderAll();
    }
  }

  // ── 碰撞避让（idle 时计算 targetOffsetY） ──
  function _recalcOffsets() {
    if (!unitFeatures.length) return;
    var placeBounds = typeof getPlaceBounds === 'function' ? getPlaceBounds() : [];
    var screenH = layers.unit ? parseInt(layers.unit.style.height) : 600;
    if (!screenH || screenH < 10) screenH = 600;
    var sp = _scaleParams(currentScale);
    var flagSize = sp.flagSize;
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
    if (ch < 10) return;
    dpr = Math.min(window.devicePixelRatio || 1, 2);
    var pw = Math.min(cw * dpr, THEME.maxPhysicalPx);
    var ph = Math.min(ch * dpr, THEME.maxPhysicalPx);
    _terrainCache = null; // 尺寸变化后重建 terrain 缓存

    ['terrain', 'route', 'unit'].forEach(function (name) {
      var canvas = layers[name];
      if (!canvas) return;
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

    // 防抖 150ms 后重绘
    clearTimeout(_resizeDebounceTimer);
    _resizeDebounceTimer = setTimeout(function () {
      _recalcOffsets();
      _renderAll();
    }, 150);
  }

  // ── 初始化 ──
  function init(mapInstance) {
    if (destroyed) return;
    map = mapInstance;
    dpr = Math.min(window.devicePixelRatio || 1, 2);

    if (typeof rough !== 'undefined') {
      roughGen = rough.generator();
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

    map.on('idle', _onMapIdle);
    map.on('resize', _onResize);

    _loadBannerImages();

    if (typeof rough !== 'undefined') {
      roughCanvas = rough.canvas(layers.unit);
    }
  }

  // ── 公开 API ──
  function setData(unitBannerFeatures, unitDirectionFeatures, placeFeatures, scale) {
    unitFeatures = unitBannerFeatures || [];
    // 构建 targetLookup: name → {lng, lat} 地理坐标（O(1) 渲染时查询）
    targetLookup = {};
    unitFeatures.forEach(function (f) {
      var name = (f.properties && f.properties.unit_name) || '';
      var coords = f.geometry && f.geometry.coordinates;
      if (name && coords && coords.length >= 2) targetLookup[name] = { lng: coords[0], lat: coords[1] };
    });
    // 从 places 数据补充地名坐标
    if (placeFeatures) {
      placeFeatures.forEach(function (f) {
        var name = (f.properties && f.properties.name) || '';
        var coords = f.geometry && f.geometry.coordinates;
        if (name && coords && coords.length >= 2) targetLookup[name] = { lng: coords[0], lat: coords[1] };
      });
    }

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
    // 预生成箭头 seed（Excalidraw 模式：种子存数据模型，拖拽/缩放不变）
    unitFeatures.forEach(function (f) {
      var props = f.properties || {};
      if (props.direction_target) {
        props._arrowSeed = _hash32('arrow-' + (props.unit_name || '') + '-' + props.direction_target);
      }
    });
    terrainFeatures = [];
    currentScale = scale || 'battle';
    _terrainCache = null; // scale 变化后重建 terrain 缓存
    _needsRender = true;
  }

  function setTimeline(step, total) {
    currentStep = step;
    totalSteps = total;
    _renderRouteAndUnit();
  }

  function resize() {
    _onResize();
  }

  function destroy() {
    destroyed = true;
    clearTimeout(_resizeDebounceTimer);
    if (map) {
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
    resize: resize,
    destroy: destroy,
    getUnitFeatures: function () { return unitFeatures; },
    THEME: THEME
  };
})();
