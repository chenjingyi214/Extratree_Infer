const els = {
  symptomFile: document.getElementById('symptom-file'),
  labFile: document.getElementById('lab-file'),
  symptomName: document.getElementById('symptom-name'),
  labName: document.getElementById('lab-name'),
  threshold: document.getElementById('threshold'),
  analyzeBtn: document.getElementById('analyze-btn'),
  demoBtn: document.getElementById('demo-btn'),
  errorBox: document.getElementById('error-box'),
  previewSection: document.getElementById('preview-section'),
  symptomsPreview: document.getElementById('symptoms-preview'),
  labsPreview: document.getElementById('labs-preview'),
  resultsSection: document.getElementById('results-section'),
  resultsBody: document.getElementById('results-body'),
  scoreSort: document.getElementById('score-sort'),
  exportBtn: document.getElementById('export-btn'),
  drawer: document.getElementById('drawer'),
  drawerClose: document.getElementById('drawer-close'),
  drawerContent: document.getElementById('drawer-content'),
};

let lastPatients = [];
let sortAsc = false;

function showError(message) {
  els.errorBox.textContent = message || '';
  els.errorBox.hidden = !message;
}

function setBusy(busy) {
  els.analyzeBtn.disabled = busy;
  els.demoBtn.disabled = busy;
  els.analyzeBtn.textContent = busy ? '分析中…' : '开始分析';
}

function setupDropzone(zoneId, input, nameEl) {
  const zone = document.getElementById(zoneId);
  zone.addEventListener('click', () => input.click());
  input.addEventListener('change', () => {
    nameEl.textContent = input.files[0] ? input.files[0].name : '点击选择或拖入文件';
  });
  zone.addEventListener('dragover', (event) => {
    event.preventDefault();
    zone.classList.add('dragover');
  });
  zone.addEventListener('dragleave', () => zone.classList.remove('dragover'));
  zone.addEventListener('drop', (event) => {
    event.preventDefault();
    zone.classList.remove('dragover');
    if (event.dataTransfer.files.length) {
      input.files = event.dataTransfer.files;
      nameEl.textContent = input.files[0].name;
    }
  });
}

function thresholdParam() {
  const value = parseFloat(els.threshold.value);
  if (Number.isNaN(value) || value < 0 || value > 1) {
    throw new Error('阈值必须是 0 到 1 之间的数值');
  }
  return value;
}

async function parseResponse(resp) {
  const data = await resp.json().catch(() => null);
  if (!resp.ok) {
    const detail = data && data.detail ? data.detail : `请求失败（HTTP ${resp.status}）`;
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail));
  }
  return data;
}

async function runDemo() {
  showError('');
  setBusy(true);
  try {
    const threshold = thresholdParam();
    const resp = await fetch(`/api/predict/demo?threshold=${threshold}`, { method: 'POST' });
    const data = await parseResponse(resp);
    renderPreview(els.symptomsPreview, data.symptoms_preview);
    renderPreview(els.labsPreview, data.labs_preview);
    els.previewSection.hidden = false;
    renderResults(data.patients);
  } catch (err) {
    showError(err.message);
  } finally {
    setBusy(false);
  }
}

async function runAnalyze() {
  showError('');
  if (!els.symptomFile.files[0] || !els.labFile.files[0]) {
    showError('请先选择症状长表和检验长表两个 CSV 文件');
    return;
  }
  setBusy(true);
  try {
    const threshold = thresholdParam();
    const form = new FormData();
    form.append('symptom_file', els.symptomFile.files[0]);
    form.append('lab_file', els.labFile.files[0]);
    const resp = await fetch(`/api/predict?threshold=${threshold}`, { method: 'POST', body: form });
    const data = await parseResponse(resp);
    els.previewSection.hidden = true;
    renderResults(data.patients);
  } catch (err) {
    showError(err.message);
  } finally {
    setBusy(false);
  }
}

function renderPreview(table, preview) {
  const head = preview.columns.map((c) => `<th>${escapeHtml(c)}</th>`).join('');
  const body = preview.rows
    .map((row) => `<tr>${row.map((cell) => `<td>${escapeHtml(cell ?? '')}</td>`).join('')}</tr>`)
    .join('');
  table.innerHTML = `<thead><tr>${head}</tr></thead><tbody>${body}</tbody>`;
}

function renderResults(patients) {
  if (!patients.length) {
    showError('未识别到有效患者记录');
    return;
  }
  lastPatients = patients.slice();
  sortAndRenderRows();
  els.resultsSection.hidden = false;
  els.resultsSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function sortAndRenderRows() {
  const rows = lastPatients.slice().sort((a, b) => (sortAsc ? a.score - b.score : b.score - a.score));
  els.scoreSort.textContent = sortAsc ? '得分 ↑' : '得分 ↓';
  els.resultsBody.innerHTML = '';
  rows.forEach((patient) => {
    const tr = document.createElement('tr');
    const badge = patient.label
      ? `<span class="badge ${patient.label === '肺炎' ? 'badge-danger' : 'badge-ok'}">${escapeHtml(patient.label)}</span>`
      : '<span class="badge badge-muted">未分类</span>';
    tr.innerHTML = `<td>${escapeHtml(patient.patient_id)}</td><td class="score">${patient.score.toFixed(4)}</td><td>${badge}</td>`;
    tr.addEventListener('click', () => openDrawer(patient));
    els.resultsBody.appendChild(tr);
  });
}

function openDrawer(patient) {
  const d = patient.detail;
  const symptoms = d.symptoms_positive.length
    ? d.symptoms_positive.map((s) => `<span class="chip">${escapeHtml(s)}</span>`).join('')
    : '<span class="muted">无阳性症状记录</span>';
  const labRows = d.labs
    .map((lab) => {
      const state = lab.measured ? '' : ' class="muted-row"';
      const value = lab.measured ? formatNum(lab.value) : '未测量';
      const normalized = lab.measured ? formatNum(lab.normalized) : '—';
      let positive = '—';
      if (lab.positive === true) positive = '<span class="badge badge-danger">阳性</span>';
      if (lab.positive === false) positive = '<span class="badge badge-ok">阴性</span>';
      return `<tr${state}><td>${escapeHtml(lab.name)}</td><td>${value}</td><td>${normalized}</td><td>${positive}</td></tr>`;
    })
    .join('');
  els.drawerContent.innerHTML = `
    <h2>${escapeHtml(patient.patient_id)}</h2>
    <p class="drawer-score">得分 <strong>${patient.score.toFixed(4)}</strong>${patient.label ? ` · ${escapeHtml(patient.label)}` : ''}</p>
    <p>年龄：${d.age ?? '未知'} · 性别：${d.gender ?? '未知'}</p>
    <h3>阳性症状</h3>
    <div class="chips">${symptoms}</div>
    <h3>检验项目</h3>
    <div class="table-scroll">
      <table class="labs-table">
        <thead><tr><th>项目</th><th>结果值</th><th>归一化</th><th>定性</th></tr></thead>
        <tbody>${labRows}</tbody>
      </table>
    </div>`;
  els.drawer.hidden = false;
}

function exportCsv() {
  const header = 'patient_id,pneumonia_score,predicted_class';
  const lines = lastPatients.map(
    (p) => [csvEscape(p.patient_id), csvEscape(p.score), csvEscape(p.label ?? '')].join(',')
  );
  const blob = new Blob(['﻿' + [header, ...lines].join('\n')], { type: 'text/csv;charset=utf-8' });
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.download = 'predictions.csv';
  link.click();
  URL.revokeObjectURL(link.href);
}

function formatNum(value) {
  if (value === null || value === undefined) return '—';
  return Number.isFinite(value) ? Math.round(value * 10000) / 10000 : '—';
}

function csvEscape(value) {
  let text = String(value ?? '');
  if (/^[=+\-@]/.test(text)) text = `'${text}`;
  if (/[",\n\r]/.test(text)) text = `"${text.replace(/"/g, '""')}"`;
  return text;
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (ch) => (
    { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch]
  ));
}

setupDropzone('symptom-zone', els.symptomFile, els.symptomName);
setupDropzone('lab-zone', els.labFile, els.labName);
els.demoBtn.addEventListener('click', runDemo);
els.analyzeBtn.addEventListener('click', runAnalyze);
els.exportBtn.addEventListener('click', exportCsv);
els.scoreSort.addEventListener('click', () => { sortAsc = !sortAsc; sortAndRenderRows(); });
els.drawerClose.addEventListener('click', () => { els.drawer.hidden = true; });
els.drawer.addEventListener('click', (event) => { if (event.target === els.drawer) els.drawer.hidden = true; });
