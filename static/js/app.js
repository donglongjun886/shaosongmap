// ShaosongMap 交互层：提取、编辑、键盘
// 依赖：utils.js → map.js → app.js（按此顺序加载）

// ── 全局报错捕获 ──
const _errorToast = document.getElementById('error-toast');
let _errorCount = 0;
window.addEventListener('error', function(e) {
  _errorCount++;
  _errorToast.innerHTML = '<span class="error-count">JS ERROR #' + _errorCount + '</span>' + escHtml(e.message) + '\n → ' + escHtml((e.filename || 'inline').replace(/^.*[\\/]/, '') + ':' + e.lineno);
  _errorToast.classList.add('show');
});
window.addEventListener('unhandledrejection', function(e) {
  _errorCount++;
  _errorToast.innerHTML = '<span class="error-count">PROMISE ERROR #' + _errorCount + '</span>' + escHtml(e.reason ? (e.reason.message || String(e.reason)) : 'Unknown');
  _errorToast.classList.add('show');
});

// ── 模式切换 ──
function switchToViewMode() {
  document.body.classList.add('mode-view');
  document.getElementById('error-msg-view').style.display = 'none';
}

function switchToInputMode() {
  document.body.classList.remove('mode-view');
  document.getElementById('error-msg-input').style.display = 'none';
}

// ── 状态 ──
let _lastExtractData = null;
let _dataModified = false;

// ── 通用 error & 分阶段进度条 ──
function showError(msg) {
  var id = document.body.classList.contains('mode-view') ? 'error-msg-view' : 'error-msg-input';
  var el = document.getElementById(id);
  el.textContent = '⚠️ ' + msg;
  el.style.display = 'block';
}

const STAGES = ['extract', 'geocode', 'render'];

function resetProgress() {
  const pp = document.getElementById('pipeline-progress');
  pp.classList.add('active');
  STAGES.forEach(s => {
    const el = document.getElementById('stage-' + s);
    el.className = 'pipeline-stage';
    const currentText = (el.textContent || '').replace(/^[✓✗⏳]\s*/, '');
    if (el.lastChild && el.lastChild.nodeType === Node.TEXT_NODE) {
      el.lastChild.textContent = currentText;
    } else {
      el.appendChild(document.createTextNode(currentText));
    }
  });
}

function setStageState(stage, state) {
  const el = document.getElementById('stage-' + stage);
  el.className = 'pipeline-stage ' + state;
  const currentText = (el.textContent || '').replace(/^[✓✗⏳]\s*/, '');
  const last = el.lastChild;
  if (last && last.nodeType === Node.TEXT_NODE) {
    if (state === 'done') last.textContent = '✓ ' + currentText;
    else if (state === 'error') last.textContent = '✗ ' + currentText;
    else if (state === 'active') last.textContent = '⏳ ' + currentText;
  } else {
    el.appendChild(document.createTextNode(''));
    const prefix = state === 'done' ? '✓ ' : state === 'error' ? '✗ ' : state === 'active' ? '⏳ ' : '';
    el.lastChild.textContent = prefix + currentText;
  }
}

// ── 提取（普通 fetch 请求/响应） ──
async function analyze() {
  const text = document.getElementById('text-input').value.trim();
  if (!text) { showError('请输入历史文本'); return; }
  const submitBtn = document.getElementById('submit-btn');
  submitBtn.disabled = true;
  document.getElementById('error-msg-input').style.display = 'none';
  document.getElementById('result-panel').style.display = 'block';
  resetProgress();

  const dynasty = document.getElementById('dynasty-select')?.value || '';

  try {
    const resp = await fetch('/api/v1/extract', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, dynasty: dynasty || null })
    });
    if (!resp.ok) { const err = await resp.json(); const msg = err.error?.message || err.detail || `请求失败 (${resp.status})`; throw new Error(msg); }
    const data = await resp.json();
    STAGES.forEach(s => setStageState(s, 'done'));
    _lastExtractData = data;
    _dataModified = false;
    renderEditableResult(data);
    switchToViewMode();
    updateMap(data);
  } catch (e) {
    showError(e.message || '服务暂不可用，请稍后重试');
    STAGES.forEach(s => {
      const el = document.getElementById('stage-' + s);
      if (!el.classList.contains('done')) setStageState(s, 'error');
    });
  } finally {
    submitBtn.disabled = false;
  }
}

// ── 可编辑结果面板（适配新字段：event_name / boundaries / person_places） ──
function renderEditableResult(data) {
  const renderBtn = document.getElementById('render-btn');
  renderBtn.disabled = true;
  renderBtn.classList.remove('active');

  // event_name 编辑框
  const nameHtml = data.event_name
    ? '<strong>事件名:</strong> <input class="editable-field" id="edit-name" value="' + escHtml(data.event_name) + '" oninput="markModified()">'
    : '<strong>事件名:</strong> <input class="editable-field" id="edit-name" placeholder="未命名" oninput="markModified()">';

  // boundaries 只读列表
  let boundariesHtml = '';
  (data.boundaries || []).forEach(function(b) {
    boundariesHtml += '<div class="boundary-item"><span class="boundary-tag">' + escHtml(b.name) + '</span>' + (b.description ? ' ' + escHtml(b.description) : '') + '</div>';
  });
  if (!boundariesHtml) boundariesHtml = '<span style="color:#999">无</span>';

  // person_places 可编辑列表（人物 → 地点 → 关系）
  let personPlacesHtml = '';
  (data.person_places || []).forEach(function(pp, i) {
    personPlacesHtml += '<div class="pp-item">' +
      '<input class="editable-field" id="edit-pp-person-' + i + '" value="' + escHtml(pp.person) + '" placeholder="人物" style="width:70px" oninput="markModified()">' +
      '<span style="margin:0 4px;color:#999">→</span>' +
      '<input class="editable-field" id="edit-pp-place-' + i + '" value="' + escHtml(pp.place) + '" placeholder="地点" style="width:80px" oninput="markModified()">' +
      '<input class="editable-field" id="edit-pp-rel-' + i + '" value="' + escHtml(pp.relation || '') + '" placeholder="关系" style="width:70px" oninput="markModified()">' +
      '<button class="del-btn" onclick="delPersonPlace(' + i + ')" title="删除">×</button>' +
      '</div>';
  });
  personPlacesHtml += '<button class="add-btn" onclick="addPersonPlace()">+人物地点</button>';

  // places 可编辑列表（保留原有逻辑）
  let placesHtml = (data.features || []).map(function(f, i) {
    const tagClass = f.source === 'chgis' ? 'tag-chgis' : f.source === 'llm_infer' ? 'tag-llm' : 'tag-unknown';
    const coords = (typeof f.lng === 'number' && typeof f.lat === 'number') ? ' (' + f.lng.toFixed(2) + ', ' + f.lat.toFixed(2) + ')' : '';
    const dataAttrs = ' data-lng="' + (f.lng ?? '') + '" data-lat="' + (f.lat ?? '') + '" data-source="' + escHtml(f.source || 'unknown') + '" data-modern-name="' + escHtml(f.modern_name || '') + '"';
    return '<span class="tag ' + tagClass + '"' + dataAttrs + '><input class="editable-field" id="edit-place-' + i + '" value="' + escHtml(f.name) + '" style="width:60px" oninput="markModified()">' + coords + '<button class="del-btn" onclick="delPlace(' + i + ')" title="删除地名">×</button></span>';
  }).join(' ');
  placesHtml += ' <button class="add-btn" onclick="addPlace()">+地名</button>';

  document.getElementById('campaign-info').innerHTML = '<div>' + nameHtml + '</div>' +
    '<div style="margin-top:8px"><strong>边界/疆域:</strong> ' + boundariesHtml + '</div>' +
    '<div style="margin-top:8px"><strong>人物→地点:</strong> <div style="margin-top:4px">' + personPlacesHtml + '</div></div>';
  document.getElementById('places-list').innerHTML = placesHtml;
}

function markModified() {
  _dataModified = true;
  const btn = document.getElementById('render-btn');
  btn.disabled = false;
  btn.classList.add('active');
}

function collectModifiedData() {
  const name = document.getElementById('edit-name')?.value || '';
  const data = {
    event_name: name || null,
    boundaries: (_lastExtractData?.boundaries || []).map(function(b) { return { name: b.name, description: b.description || '' }; }),
    person_places: [],
    places: [],
    dynasty: document.getElementById('dynasty-select')?.value || null,
    scale: _lastExtractData?.scale || null
  };

  // 收集 person_places（可编辑）
  document.querySelectorAll('[id^="edit-pp-person-"]').forEach(function(el) {
    const idx = el.id.replace('edit-pp-person-', '');
    const person = el.value.trim();
    const placeEl = document.getElementById('edit-pp-place-' + idx);
    const relEl = document.getElementById('edit-pp-rel-' + idx);
    const place = placeEl?.value.trim() || '';
    const relation = relEl?.value.trim() || '';
    if (person && place) {
      data.person_places.push({ person: person, place: place, relation: relation });
    }
  });

  // 收集 places（含坐标来源等几何信息）
  document.querySelectorAll('[id^="edit-place-"]').forEach(function(el) {
    const v = el.value.trim();
    if (!v) return;
    const tag = el.closest('.tag');
    const place = { name: v, context: '' };
    if (tag) {
      const lng = tag.getAttribute('data-lng');
      const lat = tag.getAttribute('data-lat');
      const source = tag.getAttribute('data-source');
      const modernName = tag.getAttribute('data-modern-name');
      if (lng) place.lng = parseFloat(lng);
      if (lat) place.lat = parseFloat(lat);
      if (source) place.source = source;
      if (modernName) place.modern_name = modernName;
    }
    data.places.push(place);
  });

  return data;
}

// ── 编辑操作 ──
function delPlace(i) { const el = document.getElementById('edit-place-' + i); if (el) { el.closest('.tag')?.remove(); markModified(); } }
function addPlace() {
  const container = document.getElementById('places-list');
  const btn = container.querySelector('.add-btn');
  const span = document.createElement('span');
  span.className = 'tag tag-unknown';
  const existingIds = Array.from(container.querySelectorAll('.tag input[id^="edit-place-"]')).map(function(el) { return parseInt(el.id.replace('edit-place-', '')); }).filter(function(id) { return !isNaN(id); });
  const idx = existingIds.length > 0 ? Math.max.apply(null, existingIds) + 1 : 0;
  span.innerHTML = '<input class="editable-field" id="edit-place-' + idx + '" value="新地名" style="width:60px" oninput="markModified()"><button class="del-btn" onclick="this.closest(\'.tag\').remove();markModified()">×</button>';
  btn.before(span);
  markModified();
}
function delPersonPlace(i) {
  const personEl = document.getElementById('edit-pp-person-' + i);
  if (personEl) { personEl.closest('.pp-item')?.remove(); markModified(); }
}
function addPersonPlace() {
  const container = document.getElementById('campaign-info');
  const ppItems = container.querySelectorAll('.pp-item');
  const existingIds = Array.from(ppItems).map(function(el) {
    const input = el.querySelector('input[id^="edit-pp-person-"]');
    return input ? parseInt(input.id.replace('edit-pp-person-', '')) : -1;
  }).filter(function(id) { return !isNaN(id); });
  const idx = existingIds.length > 0 ? Math.max.apply(null, existingIds) + 1 : 0;
  const addBtn = container.querySelector('.add-btn');
  if (!addBtn) return;
  const div = document.createElement('div');
  div.className = 'pp-item';
  div.innerHTML = '<input class="editable-field" id="edit-pp-person-' + idx + '" value="" placeholder="人物" style="width:70px" oninput="markModified()">' +
    '<span style="margin:0 4px;color:#999">→</span>' +
    '<input class="editable-field" id="edit-pp-place-' + idx + '" value="" placeholder="地点" style="width:80px" oninput="markModified()">' +
    '<input class="editable-field" id="edit-pp-rel-' + idx + '" value="" placeholder="关系" style="width:70px" oninput="markModified()">' +
    '<button class="del-btn" onclick="this.closest(\'.pp-item\').remove();markModified()">×</button>';
  addBtn.before(div);
  markModified();
}

// ── 重新渲染 ──
let _isRendering = false;

async function reRender() {
  if (_isRendering) return;
  _isRendering = true;
  const data = collectModifiedData();
  const btn = document.getElementById('render-btn');
  btn.disabled = true;
  btn.classList.remove('active');
  btn.textContent = '重新渲染中...';
  try {
    const resp = await fetch('/api/v1/render', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
    if (!resp.ok) { const err = await resp.json(); const msg = err.error?.message || err.detail || '渲染失败'; throw new Error(msg); }
    const result = await resp.json();
    updateMap(result);
    _lastExtractData = result;
    renderEditableResult(result);
    _dataModified = false;
    btn.textContent = '已更新';
    setTimeout(function() { btn.textContent = '重新渲染'; }, 1500);
  } catch (e) {
    showError(e.message);
    btn.textContent = '重试';
    btn.disabled = false;
  } finally {
    _isRendering = false;
  }
}

// ── 键盘快捷键 ──
document.addEventListener('keydown', function(e) {
  if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') { e.preventDefault(); analyze(); }
  if (e.key === 'Escape') {
    const tag = e.target.tagName;
    if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;
    document.querySelectorAll('.maplibregl-popup').forEach(function(p) { p.remove(); });
    document.getElementById('error-msg-input').style.display = 'none';
    document.getElementById('error-msg-view').style.display = 'none';
  }
});
