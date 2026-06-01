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
    zoom: 5,
    maxPitch: 0,
    maxBearing: 0,
    dragPan: false,
    scrollZoom: false,
    doubleClickZoom: false,
    touchZoomRotate: false,
    boxZoom: false
  });
} catch (e) {
  console.error('[map] 地图初始化失败，请检查网络或 CDN 连通性:', e.message);
  const _mapEl = document.getElementById('map');
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
/** 记录当前已应用的底图，避免重复切换导致闪烁 */
let currentBasemap = null;

function applyBasemap(name) {
  if (!map || currentBasemap === name) return;
  const provider = BASEMAP[name];
  if (!provider) return;
  const style = map.getStyle();
  // 先收集 ID 列表再逐一删除，避免活引用迭代跳过元素
  if (style && style.layers) {
    const basemapLayerIds = style.layers
      .filter(l => l.metadata && l.metadata.basemap && map.getLayer(l.id))
      .map(l => l.id);
    basemapLayerIds.forEach(id => { map.removeLayer(id); });
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
  currentBasemap = name;
}

if (map) map.on('load', () => {
  applyBasemap('muted_osm');

  // Canvas 绘制图标（替代 SVG），pixelRatio: 2 需要双倍逻辑尺寸以避免缩成半尺寸
  const iconC = document.createElement('canvas');
  iconC.width = 96; iconC.height = 96;
  const ictx = iconC.getContext('2d');
  // 城池 △
  ictx.fillStyle = '#2c2c2c';
  ictx.beginPath(); ictx.moveTo(48, 12); ictx.lineTo(84, 76); ictx.lineTo(12, 76);
  ictx.closePath(); ictx.fill();
  if (!map.hasImage('fortress')) map.addImage('fortress', ictx.getImageData(0, 0, 96, 96), { pixelRatio: 2 });
  // 营寨 ●
  ictx.clearRect(0, 0, 96, 96);
  ictx.beginPath(); ictx.arc(48, 48, 28, 0, Math.PI * 2); ictx.fill();
  if (!map.hasImage('camp')) map.addImage('camp', ictx.getImageData(0, 0, 96, 96), { pixelRatio: 2 });
  // 箭头 ▶
  const arrC = document.createElement('canvas');
  arrC.width = 48; arrC.height = 48;
  const actx = arrC.getContext('2d');
  actx.fillStyle = '#c23b22';
  actx.beginPath(); actx.moveTo(40, 24); actx.lineTo(8, 8); actx.lineTo(8, 40);
  actx.closePath(); actx.fill();
  if (!map.hasImage('arrowhead')) map.addImage('arrowhead', actx.getImageData(0, 0, 48, 48), { pixelRatio: 2 });

  map.addSource('places', { type: 'geojson', data: { type: 'FeatureCollection', features: [] } });
  map.addSource('routes', { type: 'geojson', data: { type: 'FeatureCollection', features: [] } });

  map.addLayer({
    id: 'places-chgis', type: 'symbol', source: 'places',
    filter: ['==', ['get', 'source'], 'chgis'],
    layout: { 'icon-image': 'fortress', 'icon-size': 0.78, 'icon-allow-overlap': true }
  });
  map.addLayer({
    id: 'places-llm', type: 'symbol', source: 'places',
    filter: ['==', ['get', 'source'], 'llm_infer'],
    layout: { 'icon-image': 'camp', 'icon-size': 0.78, 'icon-allow-overlap': true }
  });
  map.addLayer({
    id: 'place-labels-ancient', type: 'symbol', source: 'places',
    layout: { 'text-field': ['get', 'name'], 'text-offset': [0, 1.5], 'text-size': 13, 'visibility': 'visible' },
    paint: { 'text-color': '#2c2c2c', 'text-halo-color': '#fff', 'text-halo-width': 2 }
  });
  map.addLayer({
    id: 'place-labels-modern', type: 'symbol', source: 'places',
    filter: ['all', ['has', 'modern_name'], ['!=', ['get', 'modern_name'], '']],
    layout: { 'text-field': ['get', 'modern_name'], 'text-offset': [0, 2.8], 'text-size': 13, 'visibility': 'visible' },
    paint: { 'text-color': '#8b7355', 'text-halo-color': '#fff', 'text-halo-width': 2 }
  });
  map.addLayer({
    id: 'route-lines', type: 'line', source: 'routes',
    layout: { 'line-cap': 'butt' },
    paint: { 'line-color': '#c23b22', 'line-width': 2.5, 'line-opacity': 0.7, 'line-dasharray': [6, 3] }
  });
  map.addLayer({
    id: 'route-arrows', type: 'symbol', source: 'routes',
    layout: { 'symbol-placement': 'line', 'symbol-spacing': 180, 'icon-image': 'arrowhead', 'icon-size': 0.8 },
    paint: {}
  });

  map.addSource('route-anchors', { type: 'geojson', data: { type: 'FeatureCollection', features: [] } });
  map.addLayer({
    id: 'route-anchors', type: 'circle', source: 'route-anchors',
    paint: { 'circle-radius': 3, 'circle-color': '#c23b22', 'circle-opacity': 0.5, 'circle-stroke-width': 0 }
  });

  map.on('click', 'places-chgis', (e) => showPopup(e));
  map.on('click', 'places-llm', (e) => showPopup(e));
  map.on('mouseenter', 'places-chgis', () => { const c = map.getCanvas(); if (c) c.style.cursor = 'pointer'; });
  map.on('mouseleave', 'places-chgis', () => { const c = map.getCanvas(); if (c) c.style.cursor = ''; });
  map.on('mouseenter', 'places-llm', () => { const c = map.getCanvas(); if (c) c.style.cursor = 'pointer'; });
  map.on('mouseleave', 'places-llm', () => { const c = map.getCanvas(); if (c) c.style.cursor = ''; });
});


function updateMap(data) {
  if (!map) { console.warn('[updateMap] map not initialized, skipping'); return; }
  try {
  const geojsonFeatures = data?.geojson?.features || [];
  const placeFeatures = geojsonFeatures.filter(f =>
    f.geometry?.type === 'Point' && f.properties?._feature_type !== 'unit_banner');
  const routeFeatures = geojsonFeatures.filter(f =>
    f.geometry?.type === 'LineString' && f.properties?.type === 'route');
  map.getSource('places')?.setData({ type: 'FeatureCollection', features: placeFeatures });
  map.getSource('routes')?.setData({ type: 'FeatureCollection', features: routeFeatures });
  _safeLayout('route-lines', 'visibility', 'visible');
  _safeLayout('route-arrows', 'visibility', 'none');
  _safeLayout('route-anchors', 'visibility', 'none');
  const anchorFeatures = [];
  routeFeatures.forEach(f => {
    const coords = f.geometry?.coordinates;
    if (coords && coords.length >= 2) {
      anchorFeatures.push({ type: 'Feature', geometry: { type: 'Point', coordinates: coords[0] }, properties: {} });
      anchorFeatures.push({ type: 'Feature', geometry: { type: 'Point', coordinates: coords[coords.length - 1] }, properties: {} });
    }
  });
  map.getSource('route-anchors')?.setData({ type: 'FeatureCollection', features: anchorFeatures });
  if (basemapMode === 'auto') {
    applyBasemap('muted_osm');
  }
  if (placeFeatures.length > 0) {
    const bounds = new maplibregl.LngLatBounds();
    placeFeatures.forEach(f => { if (f.geometry?.coordinates) bounds.extend(f.geometry.coordinates); });
    routeFeatures.forEach(f => { if (f.geometry?.coordinates) f.geometry.coordinates.forEach(c => bounds.extend(c)); });
    if (!bounds.isEmpty()) map.fitBounds(bounds, { padding: 60, maxZoom: 12, animate: false });
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
  // 静态地图模式：无时间轴过滤，全部显示
  if (!map) return;
  _safeFilter('places-chgis', null);
  _safeFilter('places-llm', null);
  _safeFilter('route-lines', null);
  _safeFilter('route-arrows', null);
}

// ── 图层切换 ──
function toggleLayer(layerId, visible) { if (!map) return; map.setLayoutProperty(layerId, 'visibility', visible ? 'visible' : 'none'); }

// ── 地图销毁 ──
/** 释放 WebGL 上下文、Worker 线程、tile 缓存等资源，并解绑所有事件监听 */
function destroyMap() {
  if (!map) return;
  map.off();  // 解绑所有事件监听
  map.remove();  // 释放 WebGL/Worker/tile 资源
  map = null;
  currentBasemap = null;
}
