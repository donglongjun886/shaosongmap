// ShaosongMap 地图渲染核心
// 依赖：maplibre-gl（CDN）、utils.js（纯函数）

// ── 地图初始化（防御 CDN 加载失败） ──
let map = null;
try {
  map = new maplibregl.Map({
    container: 'map',
    style: {
      version: 8,
      glyphs: 'https://demotiles.maplibre.org/font/{fontstack}/{range}.pbf',
      sources: {},
      layers: []
    },
    center: [112, 33],
    zoom: 5
  });
} catch (e) {
  console.error('[map] 地图初始化失败，请检查网络或 CDN 连通性:', e.message);
  var _mapEl = document.getElementById('map');
  if (_mapEl) _mapEl.innerHTML = '<div style="padding:40px;text-align:center;color:#c23b22;">地图库加载失败，请刷新页面或检查网络连接</div>';
}

// ── 底图 Provider 架构 ──
const BASEMAP = {
  schematic: {
    id: 'schematic',
    sources: {},
    layers: [{ id: 'basemap-bg', type: 'background', paint: { 'background-color': '#f2e8d5' }, metadata: { basemap: true } }]
  },
  muted_osm: {
    id: 'muted_osm',
    sources: { 'basemap-osm': { type: 'raster', tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'], tileSize: 256, attribution: '© OSM' } },
    layers: [{ id: 'basemap-osm', type: 'raster', source: 'basemap-osm', paint: { 'raster-opacity': 0.25, 'raster-saturation': -1 }, metadata: { basemap: true } }]
  }
};
const SCALE_DEFAULT_BASEMAP = { tactical: 'schematic', battle: 'muted_osm', strategic: 'muted_osm' };
let basemapMode = 'auto';

function applyBasemap(name) {
  console.log('[applyBasemap] switching to:', name);
  const provider = BASEMAP[name];
  if (!provider) return;
  const style = map.getStyle();
  if (style && style.layers) {
    style.layers.filter(l => l.metadata && l.metadata.basemap).forEach(l => {
      if (map.getLayer(l.id)) map.removeLayer(l.id);
    });
  }
  if (style && style.sources) {
    Object.keys(style.sources).forEach(sid => {
      if (sid.startsWith('basemap-') && map.getSource(sid)) map.removeSource(sid);
    });
  }
  Object.entries(provider.sources).forEach(([sid, src]) => {
    if (sid) map.addSource(sid, src);
  });
  const firstDataLayer = style && style.layers ? style.layers.find(l => !(l.metadata && l.metadata.basemap)) : null;
  provider.layers.forEach(l => {
    if (firstDataLayer && firstDataLayer.id) { map.addLayer(l, firstDataLayer.id); }
    else { map.addLayer(l); }
  });
}

if (map) map.on('load', () => {
  console.log('[map.onload] map loaded, applying basemap and registering icons');
  applyBasemap('schematic');

  const ink = '#2c2c2c', ochre = '#8b4513';
  map.addImage('fortress', _makeIconSVG('fortress', ink, 32), { pixelRatio: 2 });
  map.addImage('fortress-dim', _makeIconSVG('fortress', '#aaa', 32), { pixelRatio: 2 });
  map.addImage('camp', _makeIconSVG('camp', ochre, 32), { pixelRatio: 2 });
  map.addImage('camp-dim', _makeIconSVG('camp', '#bbb', 32), { pixelRatio: 2 });
  const arrowCanvas = document.createElement('canvas');
  arrowCanvas.width = 24; arrowCanvas.height = 24;
  const actx = arrowCanvas.getContext('2d');
  actx.fillStyle = '#c23b22';
  actx.beginPath(); actx.moveTo(20, 12); actx.lineTo(4, 4); actx.lineTo(4, 20);
  actx.closePath(); actx.fill();
  map.addImage('arrowhead', actx.getImageData(0, 0, 24, 24), { pixelRatio: 2 });
  map.addImage('banner-song', _makeBannerIcon('#2b4c7e', 32), { pixelRatio: 2 });
  map.addImage('banner-jin', _makeBannerIcon('#8b4513', 32), { pixelRatio: 2 });
  map.addImage('banner-engaging', _makeBannerIcon('#c23b22', 32), { pixelRatio: 2 });
  map.addImage('banner-dim', _makeBannerIcon('#999', 32), { pixelRatio: 2 });

  map.addSource('places', { type: 'geojson', data: { type: 'FeatureCollection', features: [] } });
  map.addSource('routes', { type: 'geojson', data: { type: 'FeatureCollection', features: [] } });

  map.addLayer({
    id: 'places-chgis', type: 'symbol', source: 'places',
    filter: ['==', ['get', 'source'], 'chgis'],
    layout: { 'icon-image': 'fortress', 'icon-size': ['step', ['zoom'], 0.2, 5, 0.35, 8, 0.55, 12, 0.8], 'icon-allow-overlap': true }
  });
  map.addLayer({
    id: 'places-llm', type: 'symbol', source: 'places',
    filter: ['==', ['get', 'source'], 'llm_infer'],
    layout: { 'icon-image': 'camp', 'icon-size': ['step', ['zoom'], 0.15, 5, 0.3, 8, 0.5, 12, 0.7], 'icon-allow-overlap': true }
  });
  map.addLayer({
    id: 'place-labels-ancient', type: 'symbol', source: 'places',
    layout: { 'text-field': ['get', 'name'], 'text-offset': [0, 1.5], 'text-size': ['step', ['zoom'], 9, 5, 11, 8, 13, 12, 15], 'visibility': 'visible' },
    paint: { 'text-color': '#2c2c2c', 'text-halo-color': '#fff', 'text-halo-width': 2 }
  });
  map.addLayer({
    id: 'place-labels-modern', type: 'symbol', source: 'places',
    filter: ['!=', ['get', 'modern_name'], ''],
    layout: { 'text-field': ['get', 'modern_name'], 'text-offset': [0, 2.8], 'text-size': ['step', ['zoom'], 9, 5, 11, 8, 13, 12, 15], 'visibility': 'visible' },
    paint: { 'text-color': '#8b7355', 'text-halo-color': '#fff', 'text-halo-width': 2 }
  });
  map.addLayer({
    id: 'route-lines', type: 'line', source: 'routes',
    layout: { 'line-cap': 'butt' },
    paint: { 'line-color': '#c23b22', 'line-width': 2.5, 'line-opacity': 0.7, 'line-dasharray': [6, 3] }
  });
  map.addLayer({
    id: 'route-arrows', type: 'symbol', source: 'routes',
    layout: { 'symbol-placement': 'line', 'symbol-spacing': 180, 'icon-image': 'arrowhead', 'icon-size': 0.8, 'icon-rotate': 90 },
    paint: {}
  });

  map.addSource('unit-banners', { type: 'geojson', data: { type: 'FeatureCollection', features: [] } });
  map.addSource('unit-directions', { type: 'geojson', data: { type: 'FeatureCollection', features: [] } });

  map.addLayer({
    id: 'unit-banner-icon', type: 'symbol', source: 'unit-banners',
    layout: {
      'icon-image': ['match', ['get', 'status'],
        'engaging', 'banner-engaging',
        ['match', ['get', 'faction'], '宋', 'banner-song', '金', 'banner-jin', 'banner-song']
      ],
      'icon-size': ['step', ['zoom'], 0.2, 5, 0.35, 8, 0.55, 12, 0.8],
      'icon-allow-overlap': true,
      'icon-ignore-placement': true
    }
  });
  map.addLayer({
    id: 'unit-banner-label', type: 'symbol', source: 'unit-banners',
    layout: {
      'text-field': ['get', 'unit_name'],
      'text-offset': [0, 1.5],
      'text-size': ['step', ['zoom'], 10, 5, 12, 8, 14, 12, 16],
      'text-anchor': 'top',
      'text-allow-overlap': true,
      'text-ignore-placement': true,
      'text-optional': false
    },
    paint: { 'text-color': '#2c2c2c', 'text-halo-color': '#f2e8d5', 'text-halo-width': 2.5 }
  });
  map.addLayer({
    id: 'unit-direction-line', type: 'line', source: 'unit-directions',
    paint: {
      'line-color': ['match', ['get', 'faction'], '宋', '#2b4c7e', '金', '#8b4513', '#5a7a6a'],
      'line-width': 2, 'line-opacity': 0.7, 'line-dasharray': [6, 3]
    }
  });
  map.addLayer({
    id: 'unit-direction-arrow', type: 'symbol', source: 'unit-directions',
    layout: {
      'symbol-placement': 'line', 'symbol-spacing': 1,
      'icon-image': 'arrowhead', 'icon-size': 0.5, 'icon-rotate': 90,
      'icon-allow-overlap': true
    }
  });

  map.addSource('route-anchors', { type: 'geojson', data: { type: 'FeatureCollection', features: [] } });
  map.addLayer({
    id: 'route-anchors', type: 'circle', source: 'route-anchors',
    paint: { 'circle-radius': 3, 'circle-color': '#c23b22', 'circle-opacity': 0.5, 'circle-stroke-width': 0 }
  });

  map.addLayer({
    id: 'places-chgis-dim', type: 'symbol', source: 'places',
    filter: ['==', ['get', 'step'], -1],
    layout: { 'icon-image': 'fortress-dim', 'icon-size': ['step', ['zoom'], 0.12, 5, 0.22, 8, 0.38, 12, 0.55], 'icon-allow-overlap': true },
    paint: { 'icon-opacity': 0.35 }
  });
  map.addLayer({
    id: 'places-llm-dim', type: 'symbol', source: 'places',
    filter: ['==', ['get', 'step'], -1],
    layout: { 'icon-image': 'camp-dim', 'icon-size': ['step', ['zoom'], 0.1, 5, 0.2, 8, 0.35, 12, 0.5], 'icon-allow-overlap': true },
    paint: { 'icon-opacity': 0.35 }
  });

  map.on('click', 'places-chgis', (e) => showPopup(e));
  map.on('click', 'places-llm', (e) => showPopup(e));
  map.on('mouseenter', 'places-chgis', () => { map.getCanvas().style.cursor = 'pointer'; });
  map.on('mouseleave', 'places-chgis', () => { map.getCanvas().style.cursor = ''; });
  map.on('mouseenter', 'places-llm', () => { map.getCanvas().style.cursor = 'pointer'; });
  map.on('mouseleave', 'places-llm', () => { map.getCanvas().style.cursor = ''; });
  map.on('click', 'unit-banner-icon', (e) => showUnitPopup(e));
  map.on('mouseenter', 'unit-banner-icon', () => { map.getCanvas().style.cursor = 'pointer'; });
  map.on('mouseleave', 'unit-banner-icon', () => { map.getCanvas().style.cursor = ''; });
  console.log('[map.onload] icons, sources, layers all registered');
});

  // zoom 变化时重新计算部队偏移
  if (map) map.on('moveend', _onMapMoved);

// ── 自定义城池/营寨图标 ──
function _makeIconSVG(type, color, size) {
  const canvas = document.createElement('canvas');
  canvas.width = size; canvas.height = size;
  const ctx = canvas.getContext('2d');
  if (type === 'fortress') {
    ctx.strokeStyle = color; ctx.lineWidth = 2;
    ctx.strokeRect(3, 3, size-6, size-6);
    ctx.strokeRect(7, 7, size-14, size-14);
  } else {
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.moveTo(size/2, 3); ctx.lineTo(size-3, size-4); ctx.lineTo(3, size-4);
    ctx.closePath(); ctx.fill();
  }
  return ctx.getImageData(0, 0, size, size);
}

function _makeBannerIcon(color, size) {
  const canvas = document.createElement('canvas');
  canvas.width = size; canvas.height = size;
  const ctx = canvas.getContext('2d');
  ctx.strokeStyle = '#2c2c2c'; ctx.lineWidth = 2;
  ctx.strokeRect(3, 5, size-6, size-12);
  ctx.strokeStyle = color; ctx.lineWidth = 1.5;
  ctx.strokeRect(6, 8, size-12, size-18);
  ctx.fillStyle = color + '25';
  ctx.fillRect(6, 8, size-12, size-18);
  ctx.fillStyle = color;
  ctx.beginPath();
  ctx.moveTo(size/2, 2); ctx.lineTo(size/2+5, 7); ctx.lineTo(size/2-5, 7);
  ctx.closePath(); ctx.fill();
  return ctx.getImageData(0, 0, size, size);
}

function showPopup(e) {
  const props = e.features[0].properties;
  const sourceLabel = props.source === 'chgis' ? 'CHGIS 精确' : 'LLM 推断';
  const coords = e.features[0].geometry.coordinates.slice();
  new maplibregl.Popup()
    .setLngLat(coords)
    .setHTML('<strong>' + escHtml(props.name) + '</strong><br>来源: ' + sourceLabel + '<br>' + (props.modern_name ? '今: ' + escHtml(props.modern_name) : ''))
    .addTo(map);
}

// ── 绍宋漫画主题 ──
function _applyComicTheme(scale) {
  const wrap = document.querySelector('.map-wrap');
  const seal = document.getElementById('comic-seal');
  const legendLabel = document.getElementById('unit-legend-label');
  if (scale === 'tactical') {
    wrap.classList.add('theme-comic');
    seal.classList.remove('hidden');
    if (legendLabel) legendLabel.textContent = '部队标记';
  } else {
    wrap.classList.remove('theme-comic');
    seal.classList.add('hidden');
    if (legendLabel) legendLabel.textContent = '部队旗帜';
  }
}

function _renderSeal(name) {
  const seal = document.getElementById('comic-seal');
  const text = document.getElementById('seal-text');
  if (!name || !text) { seal.classList.add('hidden'); return; }
  const display = name.length > 4 ? name.substring(0, 4) : name;
  text.textContent = display;
  const sizes = {1: 22, 2: 18, 3: 15, 4: 13};
  text.setAttribute('font-size', sizes[display.length] || 12);
  seal.classList.remove('hidden');
}

function _renderTerrainBlocks(features, scale) {
  if (map.getLayer('terrain-fills')) map.removeLayer('terrain-fills');
  if (map.getSource('terrain-fills')) map.removeSource('terrain-fills');
  if (scale !== 'tactical') return;

  const diagonal = _computeDataDiagonal(features);
  const radiusKm = Math.max(Math.min(diagonal * 0.05, 5000), 500) / 1000;

  const fillFeatures = [];
  features.forEach(function(f) {
    const placeType = f.properties && f.properties.place_type;
    const color = _terrainColorForType(placeType);
    if (!color || !f.geometry || !f.geometry.coordinates) return;
    fillFeatures.push({
      type: 'Feature',
      geometry: { type: 'Point', coordinates: f.geometry.coordinates },
      properties: { color: color, radiusKm: radiusKm }
    });
  });
  if (fillFeatures.length === 0) return;

  map.addSource('terrain-fills', {
    type: 'geojson',
    data: { type: 'FeatureCollection', features: fillFeatures }
  });

  const style = map.getStyle();
  let beforeLayer = undefined;
  if (style && style.layers) {
    for (const l of style.layers) {
      if (!(l.metadata && l.metadata.basemap) && l.id !== 'terrain-fills') {
        beforeLayer = l.id; break;
      }
    }
  }

  map.addLayer({
    id: 'terrain-fills', type: 'circle', source: 'terrain-fills',
    paint: {
      'circle-radius': ['*', ['get', 'radiusKm'], 1000 / 0.075],
      'circle-color': ['get', 'color'],
      'circle-opacity': 0.8,
      'circle-blur': 0.5
    }
  }, beforeLayer);
}

function _makeComicUnitIcon(color, size) {
  const canvas = document.createElement('canvas');
  canvas.width = size; canvas.height = Math.round(size * 0.6);
  const ctx = canvas.getContext('2d');
  const w = canvas.width, h = canvas.height;
  const darker = _darkenColor(color, 0.15);
  ctx.fillStyle = darker;
  ctx.fillRect(0, 0, w, h);
  const bw = 2;
  ctx.fillStyle = color;
  ctx.fillRect(bw, bw, w - bw * 2, h - bw * 2);
  return ctx.getImageData(0, 0, w, h);
}

function _applyComicRouteStyle(scale) {
  if (!map.getLayer('route-lines')) return;
  if (scale === 'tactical') {
    map.setPaintProperty('route-lines', 'line-width', 3.5);
    map.setLayoutProperty('route-lines', 'line-cap', 'round');
    map.setPaintProperty('route-lines', 'line-dasharray', ['literal', [6, 3]]);
    if (map.getLayer('route-arrows')) {
      map.setLayoutProperty('route-arrows', 'icon-size', 0.96);
    }
    if (map.getLayer('unit-direction-line')) {
      map.setPaintProperty('unit-direction-line', 'line-width', 2.5);
      map.setPaintProperty('unit-direction-line', 'line-dasharray', ['literal', [1, 0]]);
      map.setPaintProperty('unit-direction-line', 'line-opacity', 0.85);
    }
    if (map.getLayer('unit-direction-arrow')) {
      map.setLayoutProperty('unit-direction-arrow', 'icon-size', 0.6);
    }
  } else {
    map.setPaintProperty('route-lines', 'line-width', 2.5);
    map.setLayoutProperty('route-lines', 'line-cap', 'butt');
    map.setPaintProperty('route-lines', 'line-dasharray', ['literal', [6, 3]]);
    if (map.getLayer('route-arrows')) {
      map.setLayoutProperty('route-arrows', 'icon-size', 0.8);
    }
    if (map.getLayer('unit-direction-line')) {
      map.setPaintProperty('unit-direction-line', 'line-width', 2);
      map.setPaintProperty('unit-direction-line', 'line-dasharray', ['literal', [6, 3]]);
      map.setPaintProperty('unit-direction-line', 'line-opacity', 0.7);
    }
    if (map.getLayer('unit-direction-arrow')) {
      map.setLayoutProperty('unit-direction-arrow', 'icon-size', 0.5);
    }
  }
}

function _applyComicLabelHalo(scale) {
  ['place-labels-ancient', 'place-labels-modern'].forEach(function(layerId) {
    if (!map.getLayer(layerId)) return;
    if (scale === 'tactical') {
      map.setPaintProperty(layerId, 'text-halo-color', 'rgba(255,255,255,0.75)');
      map.setPaintProperty(layerId, 'text-halo-width', 2.5);
      map.setPaintProperty(layerId, 'text-halo-blur', 0.5);
    } else {
      map.setPaintProperty(layerId, 'text-halo-color', '#fff');
      map.setPaintProperty(layerId, 'text-halo-width', 2);
      map.setPaintProperty(layerId, 'text-halo-blur', 0);
    }
  });
}

function _renderComicUnitMarkers(unitBannerFeatures, scale) {
  ['comic-unit-icon', 'comic-unit-label'].forEach(function(id) {
    if (map.getLayer(id)) map.removeLayer(id);
  });
  if (map.getSource('comic-unit-icons')) map.removeSource('comic-unit-icons');
  ['comic-song', 'comic-jin', 'comic-unknown', 'comic-engaging'].forEach(function(id) {
    try { if (map.hasImage(id)) map.removeImage(id); } catch(e) {}
  });

  var origVisibility = (scale === 'tactical') ? 'none' : 'visible';
  ['unit-banner-icon', 'unit-banner-label'].forEach(function(id) {
    _safeLayout(id, 'visibility', origVisibility);
  });

  if (scale !== 'tactical' || unitBannerFeatures.length === 0) { return; }

  var iconDefs = {
    'comic-song': '#2b4c7e',
    'comic-jin': '#c23b22',
    'comic-unknown': '#2c2c2c',
    'comic-engaging': '#e63946'
  };
  Object.keys(iconDefs).forEach(function(key) {
    map.addImage(key, _makeComicUnitIcon(iconDefs[key], 120), { pixelRatio: 2 });
  });

  const iconFeatures = unitBannerFeatures.map(function(f) {
    const props = f.properties || {};
    const faction = props.faction || '';
    const status = props.status || '';
    const iconKey = status === 'engaging' ? 'comic-engaging' : (faction.indexOf('宋') >= 0 ? 'comic-song' : faction.indexOf('金') >= 0 ? 'comic-jin' : 'comic-unknown');
    return {
      type: 'Feature',
      geometry: f.geometry,
      properties: Object.assign({}, props, { _icon_key: iconKey }),
    };
  });

  map.addSource('comic-unit-icons', {
    type: 'geojson',
    data: { type: 'FeatureCollection', features: iconFeatures }
  });

  var stepFilter = totalSteps > 0 ? ['==', ['get', 'step'], currentStep] : null;
  map.addLayer({
    id: 'comic-unit-icon', type: 'symbol', source: 'comic-unit-icons',
    filter: stepFilter,
    layout: {
      'icon-image': ['get', '_icon_key'],
      'icon-size': ['step', ['zoom'], 0.3, 8, 0.5, 12, 0.7],
      'icon-allow-overlap': true,
      'icon-ignore-placement': true
    }
  });

  map.addLayer({
    id: 'comic-unit-label', type: 'symbol', source: 'comic-unit-icons',
    filter: stepFilter,
    layout: {
      'text-field': ['get', 'unit_name'],
      'text-offset': [0, -1.8],
      'text-size': ['step', ['zoom'], 10, 8, 12, 12, 14],
      'text-anchor': 'center',
      'text-allow-overlap': true,
      'text-ignore-placement': true,
      'text-optional': false
    },
    paint: {
      'text-color': '#fff',
      'text-halo-color': 'rgba(0,0,0,0.55)',
      'text-halo-width': 2.0
    }
  });

  map.off('click', 'comic-unit-icon');
  map.on('click', 'comic-unit-icon', function(e) { showUnitPopup(e); });
  map.off('mouseenter', 'comic-unit-icon');
  map.on('mouseenter', 'comic-unit-icon', function() { map.getCanvas().style.cursor = 'pointer'; });
  map.off('mouseleave', 'comic-unit-icon');
  map.on('mouseleave', 'comic-unit-icon', function() { map.getCanvas().style.cursor = ''; });
}

// ── 前端自适应部队偏移 ──
let _rawBannerFeatures = null;
let _rawDirectionFeatures = null;
let _moveendTimer = null;

function _applyUnitOffsets(bannerFeatures, directionFeatures, zoom) {
  if (!bannerFeatures || bannerFeatures.length === 0) return;
  // 1. 按真实坐标分组
  var groups = {};
  bannerFeatures.forEach(function(f, i) {
    var c = f.geometry.coordinates;
    var key = c[0].toFixed(6) + ',' + c[1].toFixed(6);
    if (!groups[key]) groups[key] = [];
    groups[key].push({ idx: i, slot: (f.properties && f.properties._slot) || 0 });
  });
  // 2. 像素→度数转换
  var sumLat = 0;
  bannerFeatures.forEach(function(f) { sumLat += f.geometry.coordinates[1]; });
  var midLat = sumLat / bannerFeatures.length;
  var mPerPx = 156543 * Math.cos(midLat * Math.PI / 180) / Math.pow(2, zoom || 10);
  var isComic = document.querySelector('.map-wrap').classList.contains('theme-comic');
  var iconPx = isComic ? 84 : 26;
  var spacingDeg = (iconPx * 1.3) * mPerPx / 111320;
  // 3. 计算每个 feature 的偏移（按 unit_name+step 匹配）
  var offsetMap = {};
  Object.values(groups).forEach(function(group) {
    group.sort(function(a, b) { return a.slot - b.slot; });
    group.forEach(function(item) {
      var f = bannerFeatures[item.idx];
      var key = f.properties.unit_name + '@' + f.properties.step;
      offsetMap[key] = [0, (item.slot + 1) * spacingDeg];
    });
  });
  // 4. 应用到 banner features
  bannerFeatures.forEach(function(f) {
    var key = f.properties.unit_name + '@' + f.properties.step;
    var off = offsetMap[key];
    if (off) { f.geometry.coordinates[0] += off[0]; f.geometry.coordinates[1] += off[1]; }
  });
  // 5. 应用到 direction features
  directionFeatures.forEach(function(f) {
    var key = f.properties.unit_name + '@' + f.properties.step;
    var off = offsetMap[key];
    if (off && f.geometry.coordinates) {
      for (var i = 0; i < f.geometry.coordinates.length; i++) {
        f.geometry.coordinates[i][0] += off[0];
        f.geometry.coordinates[i][1] += off[1];
      }
    }
  });
}

function _onMapMoved() {
  if (!_rawBannerFeatures) return;
  clearTimeout(_moveendTimer);
  _moveendTimer = setTimeout(function() {
    var banners = _rawBannerFeatures.map(function(f) { return JSON.parse(JSON.stringify(f)); });
    var dirs = _rawDirectionFeatures.map(function(f) { return JSON.parse(JSON.stringify(f)); });
    _applyUnitOffsets(banners, dirs, map.getZoom());
    map.getSource('unit-banners').setData({ type: 'FeatureCollection', features: banners });
    map.getSource('unit-directions').setData({ type: 'FeatureCollection', features: dirs });
    if (map.getSource('comic-unit-icons')) {
      var comicFeatures = banners.map(function(f) {
        var props = f.properties || {};
        var faction = props.faction || '';
        var status = props.status || '';
        var iconKey = status === 'engaging' ? 'comic-engaging' :
          (faction.indexOf('宋') >= 0 ? 'comic-song' :
           faction.indexOf('金') >= 0 ? 'comic-jin' : 'comic-unknown');
        return { type: 'Feature', geometry: f.geometry,
          properties: Object.assign({}, props, { _icon_key: iconKey }) };
      });
      map.getSource('comic-unit-icons').setData({ type: 'FeatureCollection', features: comicFeatures });
    }
  }, 100);
}

function updateMap(data) {
  if (!map) { console.warn('[updateMap] map not initialized, skipping'); return; }
  try {
  console.log('[updateMap] called, geojson features:', data.geojson?.features?.length, 'scale:', data.scale);
  const geojsonFeatures = data.geojson.features || [];
  const placeFeatures = geojsonFeatures.filter(f =>
    f.geometry.type === 'Point' && f.properties?._feature_type !== 'unit_banner');
  const routeFeatures = geojsonFeatures.filter(f =>
    f.geometry.type === 'LineString' && f.properties?.type === 'route');
  const unitBannerFeatures = geojsonFeatures.filter(f =>
    f.properties?._feature_type === 'unit_banner');
  const unitDirectionFeatures = geojsonFeatures.filter(f =>
    f.properties?._feature_type === 'unit_direction');
  console.log('[updateMap] places:', placeFeatures.length, 'routes:', routeFeatures.length,
    'banners:', unitBannerFeatures.length, 'directions:', unitDirectionFeatures.length);

  // 保存原始坐标（用于 zoom 变化时重新计算偏移）
  _rawBannerFeatures = unitBannerFeatures.map(function(f) { return JSON.parse(JSON.stringify(f)); });
  _rawDirectionFeatures = unitDirectionFeatures.map(function(f) { return JSON.parse(JSON.stringify(f)); });
  // 应用当前 zoom 级别的像素偏移
  _applyUnitOffsets(unitBannerFeatures, unitDirectionFeatures, map.getZoom());

  map.getSource('places').setData({ type: 'FeatureCollection', features: placeFeatures });
  map.getSource('routes').setData({ type: 'FeatureCollection', features: routeFeatures });
  map.getSource('unit-banners').setData({ type: 'FeatureCollection', features: unitBannerFeatures });
  map.getSource('unit-directions').setData({ type: 'FeatureCollection', features: unitDirectionFeatures });
  var anchorFeatures = [];
  routeFeatures.forEach(function(f) {
    var coords = f.geometry && f.geometry.coordinates;
    if (coords && coords.length >= 2) {
      anchorFeatures.push({ type: 'Feature', geometry: { type: 'Point', coordinates: coords[0] }, properties: {} });
      anchorFeatures.push({ type: 'Feature', geometry: { type: 'Point', coordinates: coords[coords.length - 1] }, properties: {} });
    }
  });
  map.getSource('route-anchors').setData({ type: 'FeatureCollection', features: anchorFeatures });
  console.log('[updateMap] basemapMode:', basemapMode, 'scale:', data.scale);
  if (basemapMode === 'auto' && data.scale) {
    console.log('[updateMap] calling applyBasemap for:', SCALE_DEFAULT_BASEMAP[data.scale]);
    applyBasemap(SCALE_DEFAULT_BASEMAP[data.scale] || 'schematic');
    console.log('[updateMap] applyBasemap done');
  }
  _applyComicTheme(data.scale);
  _renderSeal(data.campaign_name);
  _renderTerrainBlocks(placeFeatures, data.scale);
  _renderComicUnitMarkers(unitBannerFeatures, data.scale);
  _applyComicRouteStyle(data.scale);
  _applyComicLabelHalo(data.scale);
  console.log('[updateMap] fitBounds starting');

  if (placeFeatures.length > 0) {
    const bounds = new maplibregl.LngLatBounds();
    placeFeatures.forEach(f => { if (f.geometry?.coordinates) bounds.extend(f.geometry.coordinates); });
    routeFeatures.forEach(f => { if (f.geometry?.coordinates) f.geometry.coordinates.forEach(c => bounds.extend(c)); });
    const zoomMap = { tactical: 14, battle: 10, strategic: 6 };
    const maxZoom = zoomMap[data.scale] || 10;
    map.fitBounds(bounds, { padding: 60, maxZoom: maxZoom });
  }
  applyTimelineFilters();
  } catch(e) {
    console.error('[updateMap] ERROR:', e.message, e.stack);
  }
}

function _safeFilter(layerId, filter) {
  if (!map) return;
  if (map.getLayer(layerId)) { map.setFilter(layerId, filter); }
}
function _safeLayout(layerId, prop, val) {
  if (!map) return;
  if (map.getLayer(layerId)) { map.setLayoutProperty(layerId, prop, val); }
}

function applyTimelineFilters() {
  if (!map) { console.warn('[applyTimelineFilters] map not initialized, skipping'); return; }
  if (totalSteps === 0) {
    map.setFilter('places-chgis', null);
    map.setFilter('places-llm', null);
    map.setFilter('places-chgis-dim', ['==', ['get', 'step'], -1]);
    map.setFilter('places-llm-dim', ['==', ['get', 'step'], -1]);
    map.setFilter('route-lines', null);
    map.setFilter('route-arrows', null);
    _safeFilter('unit-banner-icon', null);
    _safeFilter('unit-banner-label', null);
    _safeFilter('unit-direction-line', null);
    _safeFilter('unit-direction-arrow', null);
    return;
  }
  var activeFilter = ['any', ['<=', ['get', 'step'], currentStep], ['!', ['has', 'step']]];
  map.setFilter('places-chgis', activeFilter);
  map.setFilter('places-llm', activeFilter);
  var dimFilter = ['>', ['get', 'step'], currentStep];
  map.setFilter('places-chgis-dim', dimFilter);
  map.setFilter('places-llm-dim', dimFilter);
  map.setFilter('route-lines', activeFilter);
  map.setFilter('route-arrows', activeFilter);
  _safeFilter('unit-banner-icon', ['==', ['get', 'step'], currentStep]);
  _safeFilter('unit-banner-label', ['==', ['get', 'step'], currentStep]);
  _safeFilter('unit-direction-line', ['==', ['get', 'step'], currentStep]);
  _safeFilter('unit-direction-arrow', ['==', ['get', 'step'], currentStep]);
  _safeFilter('comic-unit-icon', ['==', ['get', 'step'], currentStep]);
  _safeFilter('comic-unit-label', ['==', ['get', 'step'], currentStep]);
}

// ── 图层切换 ──
function toggleLayer(layerId, visible) { if (!map) return; map.setLayoutProperty(layerId, 'visibility', visible ? 'visible' : 'none'); }

function toggleUnitLayers(visible) {
  var v = visible ? 'visible' : 'none';
  _safeLayout('unit-banner-icon', 'visibility', v);
  _safeLayout('unit-banner-label', 'visibility', v);
  _safeLayout('unit-direction-line', 'visibility', v);
  _safeLayout('unit-direction-arrow', 'visibility', v);
  _safeLayout('comic-unit-icon', 'visibility', v);
  _safeLayout('comic-unit-label', 'visibility', v);
}

function showUnitPopup(e) {
  var props = e.features[0].properties;
  var coords = e.lngLat;
  var statusLabels = { deploying: '待命中', marching: '进军中', engaging: '交战中', retreating: '撤退中', routing: '已溃散' };
  var statusLabel = statusLabels[props.status] || props.status;
  new maplibregl.Popup()
    .setLngLat(coords)
    .setHTML('<strong>' + escHtml(props.unit_name) + '</strong><br>' +
      '阵营: ' + escHtml(props.faction) + '<br>' +
      '状态: ' + statusLabel + '<br>' +
      '方向: ' + escHtml(props.direction || '未明确') + '<br>' +
      (props.description ? '<small>' + escHtml(props.description) + '</small>' : ''))
    .addTo(map);
}