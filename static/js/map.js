// ShaosongMap 地图渲染核心
// 依赖：maplibre-gl（CDN）、utils.js（纯函数）

// ── 地图初始化 ──
let map = null;
let maptilerKey = '';

(async function initMap() {
  // 获取 MapTiler key
  try {
    const resp = await fetch('/api/v1/config');
    if (resp.ok) {
      const cfg = await resp.json();
      maptilerKey = cfg.maptiler_key || '';
    }
  } catch (e) {
    console.warn('[map] 获取配置失败，使用 OSM 后备底图:', e.message);
  }

  // 构建底图 style：优先 MapTiler topo-v2，否则 OSM raster 后备
  const style = maptilerKey
    ? `https://api.maptiler.com/maps/topo-v2/style.json?key=${maptilerKey}`
    : {
        version: 8,
        glyphs: 'https://demotiles.maplibre.org/font/{fontstack}/{range}.pbf',
        sources: {
          'osm-raster': {
            type: 'raster',
            tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
            tileSize: 256,
            attribution: '&copy; OSM contributors'
          }
        },
        layers: [{
          id: 'osm-raster',
          type: 'raster',
          source: 'osm-raster'
        }]
      };

  try {
    map = new maplibregl.Map({
      container: 'map',
      style: style,
      center: [112, 33],
      zoom: 5,
      maxPitch: 75,
      pitch: 0,
      maxBearing: 0,
      dragPan: true,
      scrollZoom: true,
      doubleClickZoom: true,
      touchZoomRotate: false,
      boxZoom: true
    });
  } catch (e) {
    console.error('[map] 地图初始化失败，请检查网络或 CDN 连通性:', e.message);
    const _mapEl = document.getElementById('map');
    if (_mapEl) _mapEl.innerHTML = '<div style="padding:40px;text-align:center;color:#c23b22;">地图库加载失败，请刷新页面或检查网络连接</div>';
    return;
  }

  map.on('load', () => {
    // 3D 地形层（仅 MapTiler 模式下可用）
    if (maptilerKey) {
      map.addSource('terrain-dem', {
        type: 'raster-dem',
        url: `https://api.maptiler.com/tiles/terrain-rgb-v2/tiles.json?key=${maptilerKey}`
      });
      map.setTerrain({ source: 'terrain-dem', exaggeration: 1.6 });
    }

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
    // 人物关联地点高亮标记（红色圆点+白边）
    ictx.clearRect(0, 0, 96, 96);
    ictx.fillStyle = '#e74c3c';
    ictx.beginPath(); ictx.arc(48, 48, 22, 0, Math.PI * 2); ictx.fill();
    ictx.strokeStyle = '#fff';
    ictx.lineWidth = 8;
    ictx.stroke();
    if (!map.hasImage('person-marker')) map.addImage('person-marker', ictx.getImageData(0, 0, 96, 96), { pixelRatio: 2 });

    // 数据源
    map.addSource('places', { type: 'geojson', data: { type: 'FeatureCollection', features: [] } });
    map.addSource('person-places', { type: 'geojson', data: { type: 'FeatureCollection', features: [] } });
    map.addSource('boundaries', { type: 'geojson', data: { type: 'FeatureCollection', features: [] } });

    // 城池 (CHGIS) 图层
    map.addLayer({
      id: 'places-chgis', type: 'symbol', source: 'places',
      filter: ['==', ['get', 'source'], 'chgis'],
      layout: { 'icon-image': 'fortress', 'icon-size': 0.78, 'icon-allow-overlap': true }
    });
    // 营寨 (LLM) 图层
    map.addLayer({
      id: 'places-llm', type: 'symbol', source: 'places',
      filter: ['==', ['get', 'source'], 'llm_infer'],
      layout: { 'icon-image': 'camp', 'icon-size': 0.78, 'icon-allow-overlap': true }
    });
    // 古地名标签
    map.addLayer({
      id: 'place-labels-ancient', type: 'symbol', source: 'places',
      layout: { 'text-field': ['get', 'name'], 'text-offset': [0, 1.5], 'text-size': 13, 'visibility': 'visible' },
      paint: { 'text-color': '#2c2c2c', 'text-halo-color': '#fff', 'text-halo-width': 2 }
    });
    // 今地名对照标签
    map.addLayer({
      id: 'place-labels-modern', type: 'symbol', source: 'places',
      filter: ['all', ['has', 'modern_name'], ['!=', ['get', 'modern_name'], '']],
      layout: { 'text-field': ['get', 'modern_name'], 'text-offset': [0, 2.8], 'text-size': 13, 'visibility': 'visible' },
      paint: { 'text-color': '#8b7355', 'text-halo-color': '#fff', 'text-halo-width': 2 }
    });

    // 人物-地点高亮标记图层（person_places 可视化为红色圆点）
    map.addLayer({
      id: 'person-markers', type: 'symbol', source: 'person-places',
      layout: { 'icon-image': 'person-marker', 'icon-size': 0.55, 'icon-allow-overlap': true }
    });
    // 人物-地点标签（人物名 + 地名）
    map.addLayer({
      id: 'person-labels', type: 'symbol', source: 'person-places',
      layout: {
        'text-field': ['concat', ['get', 'person'], '\n', ['get', 'place']],
        'text-offset': [0, -2.2],
        'text-size': 12,
        'visibility': 'visible'
      },
      paint: { 'text-color': '#c23b22', 'text-halo-color': '#fff', 'text-halo-width': 2.5 }
    });

    // 边界虚线图层（boundaries 渲染为虚线）
    map.addLayer({
      id: 'boundary-lines', type: 'line', source: 'boundaries',
      paint: {
        'line-color': '#8b0000',
        'line-width': 2,
        'line-dasharray': [6, 4],
        'line-opacity': 0.65
      }
    });
    // 边界标签
    map.addLayer({
      id: 'boundary-labels', type: 'symbol', source: 'boundaries',
      layout: {
        'text-field': ['get', 'name'],
        'text-size': 13,
        'text-offset': [0, 0.8]
      },
      paint: { 'text-color': '#8b0000', 'text-halo-color': '#fff', 'text-halo-width': 2 }
    });

    // 点击事件
    map.on('click', 'places-chgis', (e) => showPopup(e));
    map.on('click', 'places-llm', (e) => showPopup(e));
    map.on('click', 'person-markers', (e) => showPopup(e));
    // 光标样式
    const setPointer = () => { const c = map.getCanvas(); if (c) c.style.cursor = 'pointer'; };
    const clearCursor = () => { const c = map.getCanvas(); if (c) c.style.cursor = ''; };
    map.on('mouseenter', 'places-chgis', setPointer);
    map.on('mouseleave', 'places-chgis', clearCursor);
    map.on('mouseenter', 'places-llm', setPointer);
    map.on('mouseleave', 'places-llm', clearCursor);
    map.on('mouseenter', 'person-markers', setPointer);
    map.on('mouseleave', 'person-markers', clearCursor);
  });
})();

// ── 弹窗 ──
/** 显示地点或人物关联地点的信息弹窗 */
function showPopup(e) {
  if (!map) return;
  const props = e.features[0].properties;
  const name = props.name || props.place || '';
  const person = props.person || '';
  const relation = props.relation || '';
  const modern = props.modern_name ? '<br><small>今: ' + escHtml(String(props.modern_name)) + '</small>' : '';
  const personLine = person ? '<br><small>人物: ' + escHtml(String(person)) + (relation ? ' (' + escHtml(String(relation)) + ')' : '') + '</small>' : '';
  // 防御：显示当前匹配的坐标，帮助排查同名地点覆盖问题
  const lng = e.lngLat.lng.toFixed(4);
  const lat = e.lngLat.lat.toFixed(4);
  const coordLine = '<br><small>坐标: ' + lng + ', ' + lat + '</small>';
  new maplibregl.Popup({ offset: 14 })
    .setLngLat(e.lngLat)
    .setHTML('<strong>' + escHtml(name) + '</strong>' + personLine + modern + coordLine)
    .addTo(map);
}

// ── 地图更新（适配新 API 字段：event_name / boundaries / person_places） ──
function updateMap(data) {
  if (!map) { console.warn('[updateMap] map not initialized, skipping'); return; }
  if (!map.isStyleLoaded()) {
    // 地图尚未就绪（style 加载中），延迟到 load 事件后再更新，避免数据丢失
    map.once('load', () => updateMap(data));
    return;
  }
  try {
    const geojsonFeatures = data?.geojson?.features || [];
    const personPlaces = data?.person_places || [];

    // 普通地名标记（Point 要素，非 person_place 类型）
    const placeFeatures = geojsonFeatures.filter(f =>
      f.geometry?.type === 'Point' && f.properties?._feature_type !== 'person_place');
    map.getSource('places')?.setData({ type: 'FeatureCollection', features: placeFeatures });

    // 人物-地点高亮：用 person_places 中的 place 名匹配 geojson 中的坐标
    const personPlaceFeatures = [];
    const nameCoordMap = new Map();
    geojsonFeatures.forEach(f => {
      if (f.geometry?.type === 'Point' && f.properties?.name && f.geometry?.coordinates) {
        nameCoordMap.set(f.properties.name, f.geometry.coordinates);
      }
    });
    personPlaces.forEach(pp => {
      const coords = nameCoordMap.get(pp.place);
      if (coords) {
        personPlaceFeatures.push({
          type: 'Feature',
          geometry: { type: 'Point', coordinates: coords },
          properties: {
            person: pp.person,
            place: pp.place,
            relation: pp.relation || '',
            _feature_type: 'person_place'
          }
        });
      }
    });
    map.getSource('person-places')?.setData({ type: 'FeatureCollection', features: personPlaceFeatures });

    // 边界：严格按 _feature_type 字段过滤，避免 LineString/Polygon 被误归类为边界
    const boundaryFeatures = geojsonFeatures.filter(f =>
      f.properties?._feature_type === 'boundary');
    map.getSource('boundaries')?.setData({ type: 'FeatureCollection', features: boundaryFeatures });

    // 自适应视野（包含地名、人物地点和边界）
    const allVisibleFeatures = [...placeFeatures, ...personPlaceFeatures, ...boundaryFeatures];
    if (allVisibleFeatures.length > 0) {
      const bounds = new maplibregl.LngLatBounds();
      allVisibleFeatures.forEach(f => {
        if (!f.geometry) return;
        const coords = f.geometry.coordinates;
        if (!coords) return;
        if (f.geometry.type === 'Point') {
          bounds.extend(coords);
        } else if (f.geometry.type === 'LineString') {
          coords.forEach(c => bounds.extend(c));
        } else if (f.geometry.type === 'Polygon') {
          coords[0]?.forEach(c => bounds.extend(c));
        }
      });
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

function applyTimelineFilters() {
  // 静态地图模式：无时间轴过滤，全部显示
  if (!map) return;
  _safeFilter('places-chgis', null);
  _safeFilter('places-llm', null);
}

// ── 图层切换 ──
function toggleLayer(layerId, visible) { if (!map) return; map.setLayoutProperty(layerId, 'visibility', visible ? 'visible' : 'none'); }

// ── 地图销毁 ──
/** 释放 WebGL 上下文、Worker 线程、tile 缓存等资源，并解绑所有事件监听 */
function destroyMap() {
  if (!map) return;
  map.remove();  // map.remove() 内部已解绑所有事件并释放 WebGL/Worker/tile 资源
  map = null;
}
