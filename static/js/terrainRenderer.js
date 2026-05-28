// ShaosongMap Canvas 地形渲染器
// roughjs hachure 参数梯度表达海拔高度差异（"墨分五色"）
// 依赖：roughjs（全局 rough）、CanvasRenderer

(function () {
  'use strict';

  // ── 地形 hachure 参数梯度表 ──
  var TERRAIN_PRESETS = {
    plateau: {
      // 塬（高台）：密集竖线，陡峭边缘
      fillStyle: 'hachure',
      hachureAngle: 75,
      hachureGap: 3,
      fillWeight: 0.8,
      fillColor: 'rgba(139,119,101,0.15)',
      strokeColor: '#8b766b',
      strokeWidth: 0.5
    },
    slope: {
      // 坡地：中密斜线，过渡感
      fillStyle: 'hachure',
      hachureAngle: 60,
      hachureGap: 6,
      fillWeight: 0.5,
      fillColor: 'rgba(139,119,101,0.10)',
      strokeColor: '#a09080',
      strokeWidth: 0.3
    },
    gully: {
      // 河沟：蓝色虚线（roughjs curve）
      fillStyle: 'solid',
      color: 'rgba(100,149,237,0.35)',
      strokeWidth: 2,
      dashPattern: [8, 4]
    },
    valley: {
      // 谷地：交叉阴影，凹陷感
      fillStyle: 'cross-hatch',
      hachureAngle: 45,
      hachureGap: 5,
      fillWeight: 0.4,
      fillColor: 'rgba(218,195,125,0.12)',
      strokeColor: '#b8a878',
      strokeWidth: 0.4
    },
    mountain_pass: {
      // 隘口：双线收窄
      fillStyle: 'solid',
      color: '#2c2c2c',
      strokeWidth: 1.5
    },
    flat: {
      // 平原：无纹理
      fillStyle: 'solid',
      fillColor: 'rgba(245,240,225,0.3)',
      strokeColor: 'transparent',
      strokeWidth: 0
    }
  };

  // ── roughjs 生成器缓存 ──
  var roughGen = null;
  var terrainCache = {}; // key -> { drawable, seed }

  function _getGen() {
    if (!roughGen && typeof rough !== 'undefined') {
      roughGen = rough.generator({ options: { roughness: 0.9, bowing: 0.6 } });
    }
    return roughGen;
  }

  // ── 缩放自适应参数 ──
  function _zoomAdjusted(zoom, preset) {
    var adjusted = Object.assign({}, preset);
    if (zoom >= 14) {
      // tactical: 完整细节
      adjusted.hachureGap = preset.hachureGap || 5;
      adjusted.fillWeight = preset.fillWeight || 0.8;
    } else if (zoom >= 10) {
      // battle: 简化
      adjusted.hachureGap = (preset.hachureGap || 5) * 2;
      adjusted.fillWeight = (preset.fillWeight || 0.5) * 0.6;
      adjusted.strokeWidth = (preset.strokeWidth || 0.5) * 0.7;
    } else {
      // strategic: 仅色块
      adjusted.fillStyle = 'solid';
      adjusted.fillWeight = 0.3;
      adjusted.strokeWidth = 0;
      adjusted.hachureGap = 20;
    }
    return adjusted;
  }

  // ── 渲染单个地形特征 ──
  function _renderFeature(ctx, feature, zoom) {
    var type = feature.type || 'flat';
    var preset = TERRAIN_PRESETS[type];
    if (!preset) return;

    var adjusted = _zoomAdjusted(zoom, preset);
    var gen = _getGen();
    if (!gen) return;

    // 计算屏幕尺寸
    var radiusKm = feature.radius_km || 1;
    var metersPerPx = 156543 * Math.cos((feature.center[1] || 33) * Math.PI / 180) / Math.pow(2, zoom);
    var radiusPx = Math.max((radiusKm * 1000) / metersPerPx, 30);

    var project = feature._projected; // 由调用方预计算
    if (!project) return;
    var cx = project.x;
    var cy = project.y;

    var cacheKey = type + '@' + Math.round(radiusPx / 10) * 10 + '@' + Math.round(zoom);
    var seed = _hash32str(cacheKey);

    ctx.save();
    ctx.translate(cx, cy);

    if (adjusted.fillStyle === 'solid') {
      // 简单色块
      ctx.fillStyle = adjusted.fillColor || adjusted.color || 'rgba(200,180,150,0.1)';
      ctx.beginPath();
      if (type === 'gully') {
        // 河沟：虚线
        ctx.setLineDash(adjusted.dashPattern || []);
        ctx.strokeStyle = adjusted.color;
        ctx.lineWidth = adjusted.strokeWidth;
        // 简化：绘制一个椭圆代表河沟走向
        ctx.ellipse(0, 0, radiusPx, radiusPx * 0.3, feature.direction ? _dirToRad(feature.direction) : 0, 0, Math.PI * 2);
        ctx.stroke();
        ctx.setLineDash([]);
      } else if (type === 'mountain_pass') {
        // 隘口：双线收窄
        var pw = radiusPx * 0.6;
        ctx.strokeStyle = adjusted.color;
        ctx.lineWidth = adjusted.strokeWidth;
        ctx.beginPath();
        ctx.moveTo(-pw, -radiusPx * 0.5);
        ctx.lineTo(-radiusPx * 0.3, 0);
        ctx.lineTo(-pw, radiusPx * 0.5);
        ctx.stroke();
        ctx.beginPath();
        ctx.moveTo(pw, -radiusPx * 0.5);
        ctx.lineTo(radiusPx * 0.3, 0);
        ctx.lineTo(pw, radiusPx * 0.5);
        ctx.stroke();
      } else {
        ctx.ellipse(0, 0, radiusPx, radiusPx * 0.6, 0, 0, Math.PI * 2);
        ctx.fill();
      }
    } else {
      // hachure 填充：使用 roughjs 生成
      var rectW = radiusPx * 2;
      var rectH = radiusPx * 1.2;
      var drawable = gen.rectangle(-rectW / 2, -rectH / 2, rectW, rectH, {
        fill: adjusted.fillColor,
        fillStyle: adjusted.fillStyle,
        hachureAngle: adjusted.hachureAngle,
        hachureGap: adjusted.hachureGap,
        fillWeight: adjusted.fillWeight,
        stroke: adjusted.strokeColor || 'transparent',
        strokeWidth: adjusted.strokeWidth,
        roughness: 0.9,
        seed: seed
      });

      // 直接绘制到目标 ctx（仅 zoom 变化时触发，不在热路径）
      if (typeof rough !== 'undefined') {
        var rc = rough.canvas(ctx.canvas);
        // roughjs 直接绑定了 canvas，我们手工绘制
        _drawRoughDrawable(ctx, drawable);
      }
    }

    ctx.restore();

    // 地形名称标注
    if (feature.name) {
      ctx.save();
      ctx.font = '12px "Noto Serif SC", "SimSun", serif';
      ctx.fillStyle = '#8b7355';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'top';
      ctx.fillText(feature.name, cx, cy + radiusPx * 0.6 + 4);
      ctx.restore();
    }
  }

  // ── 手动绘制 roughjs drawable ──
  function _drawRoughDrawable(ctx, drawable) {
    if (!drawable || !drawable.sets) return;
    drawable.sets.forEach(function (set) {
      switch (set.type) {
        case 'path':
          ctx.save();
          ctx.strokeStyle = set.stroke || '#000';
          ctx.lineWidth = set.strokeWidth || 1;
          ctx.fillStyle = set.fill || 'transparent';
          var path = new Path2D(set.ops);
          if (set.fill && set.fill !== 'none') ctx.fill(path);
          if (set.stroke && set.stroke !== 'none') ctx.stroke(path);
          ctx.restore();
          break;
        case 'fillPath':
          ctx.save();
          ctx.fillStyle = set.fill || '#000';
          ctx.fill(new Path2D(set.ops));
          ctx.restore();
          break;
        case 'fillSketch':
          ctx.save();
          ctx.fillStyle = set.fill || '#000';
          ctx.fill(new Path2D(set.ops));
          ctx.restore();
          break;
      }
    });
  }

  function _dirToRad(dir) {
    var mapAngles = { 'N': -Math.PI / 2, 'S': Math.PI / 2, 'E': 0, 'W': Math.PI,
                      'NE': -Math.PI / 4, 'SE': Math.PI / 4, 'NW': -3 * Math.PI / 4, 'SW': 3 * Math.PI / 4 };
    return mapAngles[dir] || 0;
  }

  function _hash32str(s) {
    var h = 0;
    for (var i = 0; i < s.length; i++) { h = ((h << 5) - h + s.charCodeAt(i)) | 0; }
    return h;
  }

  // ── 公开 API ──
  function render(ctx, features, map) {
    if (!features || !features.length || !map) return;
    var zoom = map.getZoom();

    features.forEach(function (f) {
      var coords = f.center || (f.geometry && f.geometry.coordinates);
      if (!coords) return;
      f._projected = map.project(coords);
      _renderFeature(ctx, f, zoom);
    });
  }

  window.TerrainRenderer = {
    render: render,
    TERRAIN_PRESETS: TERRAIN_PRESETS
  };
})();
