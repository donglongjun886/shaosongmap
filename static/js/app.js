// ShaosongMap 交互层：OCR、提取、编辑、时间轴、键盘
// 依赖：utils.js → map.js → app.js（按此顺序加载）

// ── 全局报错捕获 ──
const _errorToast = document.getElementById('error-toast');
let _errorCount = 0;
window.addEventListener('error', function(e) {
  _errorCount++;
  _errorToast.innerHTML = '<span class="error-count">JS ERROR #' + _errorCount + '</span>' + e.message + '\n → ' + (e.filename || 'inline').replace(/^.*[\\/]/, '') + ':' + e.lineno;
  _errorToast.classList.add('show');
});
window.addEventListener('unhandledrejection', function(e) {
  _errorCount++;
  _errorToast.innerHTML = '<span class="error-count">PROMISE ERROR #' + _errorCount + '</span>' + (e.reason ? (e.reason.message || String(e.reason)) : 'Unknown');
  _errorToast.classList.add('show');
});

// ── 模式切换 ──
function switchToViewMode() {
  document.body.classList.add('mode-view');
  document.getElementById('map-guide').classList.add('hidden');
  document.getElementById('error-msg-view').style.display = 'none';
}

function switchToInputMode() {
  document.body.classList.remove('mode-view');
  document.getElementById('map-guide').classList.remove('hidden');
  document.getElementById('error-msg-input').style.display = 'none';
}

// ── 多截图批量处理 ──
const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');
const ocrProgress = document.getElementById('ocr-progress');
const ocrProgressText = document.getElementById('ocr-progress-text');

let _imageBatch = [];

dropZone.addEventListener('dragover', (e) => { e.preventDefault(); dropZone.classList.add('dragover'); });
dropZone.addEventListener('dragleave', () => { dropZone.classList.remove('dragover'); });
dropZone.addEventListener('drop', (e) => {
  e.preventDefault();
  dropZone.classList.remove('dragover');
  if (e.dataTransfer.files.length > 0) {
    for (const file of e.dataTransfer.files) addToBatch(file);
  }
});

document.addEventListener('paste', (e) => {
  if (document.activeElement?.tagName === 'TEXTAREA' || document.activeElement?.tagName === 'INPUT') return;
  const items = e.clipboardData?.items;
  if (!items) return;
  for (const item of items) {
    if (item.type.startsWith('image/')) {
      e.preventDefault();
      addToBatch(item.getAsFile());
    }
  }
});

function handleFileSelect(e) {
  for (const file of e.target.files) addToBatch(file);
  fileInput.value = '';
}

async function addToBatch(file) {
  if (!file.type.match(/image\/(png|jpeg)/)) { showError('仅支持 PNG 和 JPEG 格式'); return; }
  if (_imageBatch.length >= 10) { showError('每次最多添加 10 张截图'); return; }
  var errorEl = document.getElementById('error-msg-input');
  errorEl.style.display = 'none';
  const resized = await resizeImage(file, 1920);
  const dataUrl = await new Promise((resolve) => {
    const reader = new FileReader();
    reader.onload = (e) => resolve(e.target.result);
    reader.readAsDataURL(resized);
  });
  _imageBatch.push({ blob: resized, dataUrl });
  renderThumbnails();
}

function removeFromBatch(index) { _imageBatch.splice(index, 1); renderThumbnails(); }

function renderThumbnails() {
  const list = document.getElementById('thumb-list');
  const controls = document.getElementById('batch-controls');
  if (_imageBatch.length === 0) { list.innerHTML = ''; controls.classList.remove('active'); return; }
  list.innerHTML = _imageBatch.map((item, i) =>
    `<div class="thumb-item">
      <img src="${item.dataUrl}" alt="截图${i + 1}">
      <span class="thumb-idx">${i + 1}</span>
      <button class="thumb-del" onclick="event.stopPropagation();removeFromBatch(${i})" title="删除">×</button>
    </div>`
  ).join('');
  controls.classList.add('active');
}

function clearBatch() {
  _imageBatch = [];
  renderThumbnails();
  document.getElementById('batch-review').classList.remove('active');
  document.getElementById('error-msg-input').style.display = 'none';
  ocrProgress.classList.remove('active');
}

async function resizeImage(file, maxDim) {
  return new Promise((resolve) => {
    const img = new Image();
    const url = URL.createObjectURL(file);
    img.onload = () => {
      URL.revokeObjectURL(url);
      let { width, height } = img;
      if (width <= maxDim && height <= maxDim) { resolve(file); return; }
      const ratio = Math.min(maxDim / width, maxDim / height);
      width = Math.round(width * ratio);
      height = Math.round(height * ratio);
      const canvas = document.createElement('canvas');
      canvas.width = width; canvas.height = height;
      const ctx = canvas.getContext('2d');
      ctx.drawImage(img, 0, 0, width, height);
      canvas.toBlob((blob) => resolve(blob), file.type, 0.85);
    };
    img.onerror = function() { URL.revokeObjectURL(url); };
    img.src = url;
  });
}

async function startBatchOCR() {
  if (_imageBatch.length === 0) return;
  var errorEl = document.getElementById('error-msg-input');
  errorEl.style.display = 'none';
  ocrProgress.classList.add('active');
  ocrProgressText.textContent = `正在识别第 1/${_imageBatch.length} 张截图…`;
  document.getElementById('batch-progress-fill').style.width = '0%';
  document.getElementById('batch-controls').classList.remove('active');
  document.querySelectorAll('.thumb-status').forEach(el => el.remove());
  _abortPrevious();
  const controller = new AbortController();
  _activeAbortController = controller;

  try {
    const formData = new FormData();
    _imageBatch.forEach((item, i) => formData.append('files', item.blob, `screenshot_${i + 1}.png`));
    const resp = await fetch('/api/v1/ocr/batch', { method: 'POST', body: formData, signal: controller.signal });
    if (!resp.ok) { const err = await resp.json(); const msg = err.error?.message || err.detail || '批量识别失败'; throw new Error(msg); }
    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    while (true) {
      if (controller.signal.aborted) { return; }
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';
      let eventType = '', eventData = '';
      for (const line of lines) {
        if (line.startsWith('event: ')) { eventType = line.slice(7); }
        else if (line.startsWith('data: ')) {
          eventData = line.slice(6);
          if (eventType && eventData) { try { handleBatchSSE(eventType, JSON.parse(eventData)); } catch (_) {} }
          eventType = ''; eventData = '';
        }
      }
    }
  } catch (e) {
    if (e.name === 'AbortError') return;
    showError(e.message || '批量识别失败，请重试');
    ocrProgress.classList.remove('active');
    document.getElementById('batch-controls').classList.add('active');
  } finally {
    _activeAbortController = null;
  }
}

function handleBatchSSE(type, data) {
  if (type === 'progress') {
    const pct = Math.round((data.current / data.total) * 100);
    ocrProgressText.textContent = `正在识别第 ${data.current}/${data.total} 张截图（${data.char_count} 字）…`;
    document.getElementById('batch-progress-fill').style.width = pct + '%';
    const items = document.querySelectorAll('.thumb-item');
    if (items[data.current - 1]) {
      const status = document.createElement('div');
      status.className = 'thumb-status';
      status.textContent = '✓ ' + data.char_count + '字';
      items[data.current - 1].appendChild(status);
    }
  } else if (type === 'merge') {
    ocrProgressText.textContent = `去重拼接完成：${data.original_chars} → ${data.merged_chars} 字（去除 ${data.removed_dup} 字重复）`;
  } else if (type === 'complete') {
    ocrProgress.classList.remove('active');
    document.getElementById('review-text').value = data.text;
    document.getElementById('review-stats').textContent = `共 ${data.text.length} 字`;
    document.getElementById('batch-review').classList.add('active');
  } else if (type === 'error') {
    showError(data.message || '批量识别失败');
    ocrProgress.classList.remove('active');
    document.getElementById('batch-controls').classList.add('active');
  }
}

function confirmBatchText() {
  const text = document.getElementById('review-text').value.trim();
  if (!text) { showError('识别结果为空白，请重新截图'); return; }
  document.getElementById('text-input').value = text;
  document.getElementById('batch-review').classList.remove('active');
  clearBatch();
}

function cancelReview() {
  document.getElementById('batch-review').classList.remove('active');
  document.getElementById('batch-controls').classList.add('active');
}

// ── 状态 ──
let _lastExtractData = null;
let _dataModified = false;
let currentStep = 1;
let totalSteps = 0;
let _events = [];
let _units = [];
let _unitStates = [];
let _activeAbortController = null;
function _abortPrevious() {
  if (_activeAbortController) {
    _activeAbortController.abort();
    _activeAbortController = null;
  }
}

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
    el.lastChild.textContent = el.lastChild.textContent.replace(/^[✓✗⏳]\s*/, '');
  });
}

function setStageState(stage, state) {
  const el = document.getElementById('stage-' + stage);
  el.className = 'pipeline-stage ' + state;
  const text = el.lastChild.textContent.replace(/^[✓✗⏳]\s*/, '');
  if (state === 'done') el.lastChild.textContent = '✓ ' + text;
  else if (state === 'error') el.lastChild.textContent = '✗ ' + text;
  else if (state === 'active') el.lastChild.textContent = '⏳ ' + text;
}

// ── SSE 提取 ──
async function analyze() {
  const text = document.getElementById('text-input').value.trim();
  if (!text) { showError('请输入战役文本或上传截图'); return; }
  const submitBtn = document.getElementById('submit-btn');
  submitBtn.disabled = true;
  document.getElementById('error-msg-input').style.display = 'none';
  document.getElementById('result-panel').style.display = 'block';
  resetProgress();

  const dynasty = document.getElementById('dynasty-select').value;

  _abortPrevious();
  const controller = new AbortController();
  _activeAbortController = controller;

  try {
    const resp = await fetch('/api/v1/extract', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, dynasty: dynasty || null }),
      signal: controller.signal
    });
    if (!resp.ok) { const err = await resp.json(); const msg = err.error?.message || err.detail || `请求失败 (${resp.status})`; throw new Error(msg); }
    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    while (true) {
      if (controller.signal.aborted) { return; }
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';
      let eventType = '', eventData = '';
      for (const line of lines) {
        if (line.startsWith('event: ')) { eventType = line.slice(7); }
        else if (line.startsWith('data: ')) {
          eventData = line.slice(6);
          if (eventType === 'progress' || eventType === 'result' || eventType === 'error') {
            try { const data = JSON.parse(eventData); handleSSEEvent(eventType, data); } catch (e) { console.error('[SSE] handleSSEEvent error:', e.message, e.stack); }
          }
          eventType = ''; eventData = '';
        }
      }
    }
  } catch (e) {
    if (e.name === 'AbortError') return;
    showError(e.message || '服务暂不可用，请稍后重试');
    STAGES.forEach(s => {
      const el = document.getElementById('stage-' + s);
      if (el.classList.contains('active')) setStageState(s, 'error');
    });
  } finally {
    _activeAbortController = null;
    submitBtn.disabled = false;
  }
}

function handleSSEEvent(type, data) {
  if (type === 'progress') {
    const stageOrder = {'extract_done': 'extract', 'geocode_done': 'geocode', 'render_done': 'render'};
    const mappedStage = stageOrder[data.stage] || data.stage;
    setStageState(mappedStage, 'ok' in data && !data.ok ? 'error' : 'done');
    const idx = STAGES.indexOf(mappedStage);
    if (idx >= 0 && idx + 1 < STAGES.length) { setStageState(STAGES[idx + 1], 'active'); }
  } else if (type === 'error') {
    const stageMap = {extract: 'extract', geocode: 'geocode', render: 'render'};
    const stage = stageMap[data.stage] || 'extract';
    setStageState(stage, 'error');
    showError(data.message || '处理失败');
  } else if (type === 'result') {
    setStageState('render', 'done');
    _lastExtractData = data;
    _dataModified = false;
    document.getElementById('scale-indicator').textContent = '';
    document.getElementById('timeline-wrap').classList.remove('active');
    document.getElementById('unit-card').style.display = 'none';
    renderEditableResult(data);
    switchToViewMode();
    updateMap(data);
  }
}

// ── 可编辑结果面板 ──
function renderEditableResult(data) {
  const renderBtn = document.getElementById('render-btn');
  renderBtn.disabled = true;
  renderBtn.classList.remove('active');

  const nameHtml = data.campaign_name
    ? `<strong>战役名:</strong> <input class="editable-field" id="edit-name" value="${escHtml(data.campaign_name)}" oninput="markModified()">`
    : `<strong>战役名:</strong> <input class="editable-field" id="edit-name" placeholder="未命名" oninput="markModified()">`;

  let factionsHtml = '';
  data.factions.forEach((f, fi) => {
    const commanders = f.commanders.map((c, ci) =>
      `<input class="editable-field" id="edit-cmd-${fi}-${ci}" value="${escHtml(c)}" oninput="markModified()"><button class="del-btn" onclick="delCommander(${fi},${ci})" title="删除将领">×</button>`
    ).join('');
    factionsHtml += `<div style="margin:4px 0"><strong>${escHtml(f.name)}:</strong> 将领: ${commanders}<button class="add-btn" onclick="addCommander(${fi})">+将领</button> 兵力: <input class="editable-field" id="edit-troops-${fi}" value="${escHtml(f.troops || '')}" placeholder="未知" oninput="markModified()"></div>`;
  });

  let unitsHtml = '';
  const units = data.units || [];
  if (units.length > 0) {
    const unitRows = units.map((u, ui) => {
      const factionColor = (u.faction || '').includes('宋') ? '#2b4c7e' : (u.faction || '').includes('金') ? '#8b4513' : '#5a7a6a';
      const typeLabel = {infantry: '步', cavalry: '骑', mixed: '混'}[u.troop_type] || '?';
      return `<div style="margin:2px 0;font-size:13px">
        <span style="display:inline-block;width:8px;height:8px;background:${factionColor};margin-right:4px;vertical-align:middle"></span>
        <strong>${escHtml(u.name)}</strong>
        ${u.commander ? `<span style="color:#555">· ${escHtml(u.commander)}</span>` : ''}
        <span style="display:inline-block;padding:0 4px;border-radius:2px;font-size:10px;background:#e8e0d0;margin:0 2px">${typeLabel}</span>
        ${u.troop_count ? `<span style="color:#888;font-size:11px">${escHtml(u.troop_count)}</span>` : ''}
      </div>`;
    }).join('');
    unitsHtml = `<div style="margin-top:8px;padding-top:8px;border-top:1px solid #d5c8b0"><strong style="font-size:13px">⚔️ 部队编制</strong>${unitRows}</div>`;
  }

  let placesHtml = data.features.map((f, i) => {
    const tagClass = f.source === 'chgis' ? 'tag-chgis' : f.source === 'llm_infer' ? 'tag-llm' : 'tag-unknown';
    const coords = f.lng ? ` (${f.lng.toFixed(2)}, ${f.lat.toFixed(2)})` : '';
    return `<span class="tag ${tagClass}"><input class="editable-field" id="edit-place-${i}" value="${escHtml(f.name)}" style="width:60px" oninput="markModified()">${coords}<button class="del-btn" onclick="delPlace(${i})" title="删除地名">×</button></span>`;
  }).join(' ');
  placesHtml += ` <button class="add-btn" onclick="addPlace()">+地名</button>`;

  let routesHtml = '';
  data.routes.forEach((r, i) => {
    routesHtml += `<div style="margin:2px 0">📌 <input class="editable-field" id="edit-route-from-${i}" value="${escHtml(r.from_place)}" style="width:60px" oninput="markModified()"> → <input class="editable-field" id="edit-route-to-${i}" value="${escHtml(r.to_place)}" style="width:60px" oninput="markModified()"><button class="del-btn" onclick="delRoute(${i})" title="删除路线">×</button></div>`;
  });
  if (!routesHtml) routesHtml = '未检测到行军路线';
  routesHtml += ` <button class="add-btn" onclick="addRoute()">+路线</button>`;

  document.getElementById('campaign-info').innerHTML = `<div>${nameHtml}${factionsHtml}${unitsHtml}</div>`;
  document.getElementById('places-list').innerHTML = placesHtml;
  document.getElementById('routes-list').innerHTML = routesHtml;
}

function markModified() {
  _dataModified = true;
  const btn = document.getElementById('render-btn');
  btn.disabled = false;
  btn.classList.add('active');
}

function collectModifiedData() {
  const name = document.getElementById('edit-name')?.value || '';
  const data = { campaign_name: name || null, factions: [], places: [], routes: [], dynasty: document.getElementById('dynasty-select').value || null, scale: _lastExtractData?.scale || null };
  if (_lastExtractData) {
    _lastExtractData.factions.forEach((f, fi) => {
      const commanders = [];
      let ci = 0;
      while (true) { const el = document.getElementById(`edit-cmd-${fi}-${ci}`); if (!el) break; const v = el.value.trim(); if (v) commanders.push(v); ci++; }
      const troopsEl = document.getElementById(`edit-troops-${fi}`);
      data.factions.push({ name: f.name, commanders, troops: troopsEl?.value.trim() || null });
    });
  }
  let pi = 0;
  while (true) { const el = document.getElementById(`edit-place-${pi}`); if (!el) break; const v = el.value.trim(); if (v) data.places.push({ name: v, context: '' }); pi++; }
  let ri = 0;
  while (true) {
    const fromEl = document.getElementById(`edit-route-from-${ri}`);
    const toEl = document.getElementById(`edit-route-to-${ri}`);
    if (!fromEl || !toEl) break;
    const from = fromEl.value.trim(); const to = toEl.value.trim();
    if (from && to) data.routes.push({ from, to, via: [] });
    ri++;
  }
  return data;
}

// ── 编辑操作 ──
function delPlace(i) { const el = document.getElementById(`edit-place-${i}`); if (el) { el.closest('.tag')?.remove(); markModified(); } }
function addPlace() {
  const container = document.getElementById('places-list');
  const btn = container.querySelector('.add-btn');
  const span = document.createElement('span');
  span.className = 'tag tag-unknown';
  const idx = container.querySelectorAll('.tag').length;
  span.innerHTML = `<input class="editable-field" id="edit-place-${idx}" value="新地名" style="width:60px" oninput="markModified()"><button class="del-btn" onclick="this.closest('.tag').remove();markModified()">×</button>`;
  btn.before(span);
  markModified();
}
function delCommander(fi, ci) { const el = document.getElementById(`edit-cmd-${fi}-${ci}`); if (el) { el.previousElementSibling?.remove(); el.nextElementSibling?.remove(); el.remove(); markModified(); } }
function addCommander(fi) {
  let ci = 0;
  while (document.getElementById(`edit-cmd-${fi}-${ci}`)) ci++;
  const parent = document.querySelector(`[onclick="addCommander(${fi})"]`).parentNode;
  const span = document.createElement('span');
  span.innerHTML = `<input class="editable-field" id="edit-cmd-${fi}-${ci}" value="新将领" oninput="markModified()"><button class="del-btn" onclick="this.previousElementSibling.remove();this.remove();markModified()">×</button>`;
  parent.querySelector('.add-btn').before(span);
  markModified();
}
function delRoute(i) { const fromEl = document.getElementById(`edit-route-from-${i}`); if (fromEl) fromEl.closest('div').remove(); markModified(); }
function addRoute() {
  const container = document.getElementById('routes-list');
  let ri = container.querySelectorAll('[id^="edit-route-from-"]').length;
  const div = document.createElement('div');
  div.style.margin = '2px 0';
  div.innerHTML = `📌 <input class="editable-field" id="edit-route-from-${ri}" value="起点" style="width:60px" oninput="markModified()"> → <input class="editable-field" id="edit-route-to-${ri}" value="终点" style="width:60px" oninput="markModified()"><button class="del-btn" onclick="this.parentElement.remove();markModified()">×</button>`;
  const btn = container.querySelector('.add-btn');
  btn.before(div);
  markModified();
}

// ── 重新渲染 ──
async function reRender() {
  const data = collectModifiedData();
  const btn = document.getElementById('render-btn');
  btn.disabled = true;
  btn.classList.remove('active');
  btn.textContent = '⏳ 重新渲染中...';
  try {
    const resp = await fetch('/api/v1/render', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
    if (!resp.ok) { const err = await resp.json(); const msg = err.error?.message || err.detail || '渲染失败'; throw new Error(msg); }
    const result = await resp.json();
    _lastExtractData = result;
    _dataModified = false;
    document.getElementById('timeline-wrap').classList.remove('active');
    _applyComicTheme(null);
    _renderSeal(result.campaign_name);
    updateMap(result);
    btn.textContent = '✓ 已更新';
    setTimeout(() => { btn.textContent = '🔄 重新渲染'; }, 1500);
  } catch (e) {
    showError(e.message);
    btn.textContent = '🔄 重试';
    btn.disabled = false;
  }
}

// ── 键盘快捷键 ──
document.addEventListener('keydown', (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') { e.preventDefault(); analyze(); }
  if (e.key === 'Escape') {
    document.querySelectorAll('.maplibregl-popup').forEach(p => p.remove());
    document.getElementById('error-msg-input').style.display = 'none';
    document.getElementById('error-msg-view').style.display = 'none';
  }
  if (totalSteps === 0) return;
  if (e.key === 'ArrowLeft') { e.preventDefault(); stepTo(currentStep - 1); }
  if (e.key === 'ArrowRight') { e.preventDefault(); stepTo(currentStep + 1); }
});

// ── 时间轴交互 ──
function stepTo(step) {
  if (step < 1 || step > totalSteps) return;
  currentStep = step;
  applyTimelineFilters();
  renderEventCard(currentStep);
  renderUnitStateCard(currentStep);
  updateTimelineBar();
  updateStepButtons();
}

function renderTimeline() {
  var bar = document.getElementById('timeline-bar');
  var html = '';
  for (var i = 1; i <= totalSteps; i++) {
    if (i > 1) { var lineClass = (i <= currentStep) ? 'timeline-line done' : 'timeline-line'; html += '<div class="' + lineClass + '"></div>'; }
    var nodeClass = 'timeline-node';
    if (i < currentStep) nodeClass += ' done';
    else if (i === currentStep) nodeClass += ' current';
    else nodeClass += ' pending';
    var ev = _events[i - 1] || {};
    var typeLabel = {march: '行军', battle: '战斗', encamp: '扎营', retreat: '撤退'}[ev.event_type] || '';
    html += '<div class="' + nodeClass + '" onclick="stepTo(' + i + ')" title="' + typeLabel + ': ' + (ev.description || '') + '"><span class="dot"></span><span class="timeline-node-label">T' + i + '</span></div>';
  }
  bar.innerHTML = html;
  updateStepButtons();
  renderEventCard(currentStep);
}

function updateTimelineBar() {
  var nodes = document.querySelectorAll('.timeline-node');
  var lines = document.querySelectorAll('.timeline-line');
  nodes.forEach(function(node, i) {
    var step = i + 1;
    node.classList.remove('done', 'current', 'pending');
    if (step < currentStep) node.classList.add('done');
    else if (step === currentStep) node.classList.add('current');
    else node.classList.add('pending');
  });
  lines.forEach(function(line, i) { line.classList.toggle('done', (i + 1) < currentStep); });
}

function updateStepButtons() {
  document.getElementById('btn-prev').disabled = (currentStep <= 1);
  document.getElementById('btn-next').disabled = (currentStep >= totalSteps);
  document.getElementById('step-indicator').textContent = '● ' + currentStep + '/' + totalSteps;
}

function renderEventCard(step) {
  var card = document.getElementById('event-card');
  if (!_events || step < 1 || step > _events.length) { card.style.display = 'none'; return; }
  card.style.display = 'block';
  var ev = _events[step - 1];
  var typeLabels = {march: '行军', battle: '战斗', encamp: '扎营', retreat: '撤退'};
  var typeLabel = typeLabels[ev.event_type] || ev.event_type;
  var typeClass = 'event-type-' + ev.event_type;
  var actorsHtml = (ev.actors || []).length > 0 ? '<span>🎯 ' + ev.actors.join('、') + '</span>' : '';
  var placesHtml = (ev.places_involved || []).length > 0 ? '<span>📍 ' + ev.places_involved.join('、') + '</span>' : '';
  card.innerHTML = '<span class="event-type ' + typeClass + '">' + typeLabel + '</span><strong>T' + ev.seq + '</strong>' +
    '<div class="event-desc">' + escHtml(ev.description || '') + '</div>' +
    '<div class="event-meta">' + actorsHtml + placesHtml + '</div>';
}

function renderUnitStateCard(step) {
  var card = document.getElementById('unit-card');
  if (!_unitStates || _unitStates.length === 0) { card.style.display = 'none'; return; }
  var stepStates = _unitStates.filter(function(us) { return us.seq === step; });
  if (stepStates.length === 0) { card.style.display = 'none'; return; }
  card.style.display = 'block';
  var statusLabels = { deploying: '待命', marching: '进军', engaging: '交战', retreating: '撤退', routing: '溃散' };
  var statusColors = { deploying: '#f0ad4e', marching: '#3b82f6', engaging: '#ef4444', retreating: '#a855f7', routing: '#999' };
  var rows = stepStates.map(function(us) {
    var color = statusColors[us.status] || '#999';
    var label = statusLabels[us.status] || us.status;
    return '<div style="margin:6px 0;display:flex;align-items:flex-start;gap:8px">' +
      '<span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:' + color + ';flex-shrink:0;margin-top:3px"></span>' +
      '<div><strong>' + escHtml(us.unit_name) + '</strong> ' +
      '<span style="display:inline-block;padding:1px 6px;border-radius:3px;font-size:11px;background:' + color + ';color:#fff">' + label + '</span>' +
      '<div style="font-size:12px;color:#555;margin-top:2px">' + (us.description || '') + '</div>' +
      (us.location ? '<span style="font-size:11px;color:#888">📍 ' + escHtml(us.location) + '</span>' : '') +
      '</div></div>';
  });
  card.innerHTML = '<div style="font-size:13px;font-weight:bold;margin-bottom:6px">⚔️ 部队动态 (T' + step + ')</div>' + rows.join('');
}
