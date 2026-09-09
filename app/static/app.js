const SYMPTOMS = [
  '乏力', '低热', '呼吸困难', '咳嗽', '咳痰', '喷嚏', '头晕/疼',
  '憋气', '气短', '流涕', '胸痛', '鼻塞', '意识模糊/嗜睡',
];

const QUANT_LABS = [
  '白细胞计数', '中性粒细胞计数', '淋巴细胞计数', '单核细胞计数',
  '血小板计数', '血小板分布宽度', '红细胞比容', 'C反应蛋白', '淀粉样蛋白A',
];
const QUAL_LAB = '肺炎支原体抗体.IgM';

const DEMO_FY13 = {
  age: 91,
  gender: '女',
  symptoms: ['乏力', '低热', '呼吸困难', '咳嗽', '头晕/疼', '憋气', '气短', '意识模糊/嗜睡'],
  labs: {
    '白细胞计数': 6.93, '红细胞比容': 35.4, '淋巴细胞计数': 1.3,
    '单核细胞计数': 0.43, '中性粒细胞计数': 5.06, '血小板分布宽度': 10.8,
    '血小板计数': 137, '淀粉样蛋白A': 11.273, 'C反应蛋白': 2.2,
  },
  qualLab: '',
};

const els = {
  form: document.getElementById('patient-form'),
  age: document.getElementById('age'),
  genderSeg: document.getElementById('gender-seg'),
  symptomList: document.getElementById('symptom-list'),
  labGrid: document.getElementById('lab-grid'),
  threshold: document.getElementById('threshold'),
  submitBtn: document.getElementById('submit-btn'),
  demoFy: document.getElementById('demo-fy'),
  resetBtn: document.getElementById('reset-btn'),
  errorBox: document.getElementById('error-box'),
  resultSection: document.getElementById('result-section'),
  resultContent: document.getElementById('result-content'),
};

function showError(message) {
  els.errorBox.classList.remove('info-box');
  els.errorBox.textContent = message || '';
  els.errorBox.hidden = !message;
}

function setBusy(busy) {
  els.submitBtn.disabled = busy;
  els.submitBtn.textContent = busy ? '评分中…' : '提交评分';
}

function setSeg(seg, value) {
  seg.querySelectorAll('.seg-btn').forEach((btn) => {
    btn.classList.toggle('active', btn.dataset.value === value);
  });
}

function segValue(seg) {
  const active = seg.querySelector('.seg-btn.active');
  return active ? active.dataset.value : null;
}

function buildForm() {
  SYMPTOMS.forEach((name) => {
    const row = document.createElement('div');
    row.className = 'symptom-row';
    row.innerHTML = `
      <span class="symptom-name">${name}</span>
      <div class="seg seg-sm" data-symptom="${name}">
        <button type="button" class="seg-btn active" data-value="0">无</button>
        <button type="button" class="seg-btn" data-value="1">有</button>
      </div>`;
    els.symptomList.appendChild(row);
  });

  QUANT_LABS.forEach((name) => {
    const label = document.createElement('label');
    label.className = 'field lab-field';
    label.innerHTML = `
      <span class="field-label">${name}</span>
      <input type="number" step="any" data-lab="${name}" placeholder="未测" />`;
    els.labGrid.appendChild(label);
  });

  const qualLabel = document.createElement('label');
  qualLabel.className = 'field lab-field';
  qualLabel.innerHTML = `
    <span class="field-label">肺炎支原体抗体 IgM</span>
    <select id="qual-lab">
      <option value="">未测</option>
      <option value="阴性">阴性</option>
      <option value="阳性">阳性</option>
    </select>`;
  els.labGrid.appendChild(qualLabel);
}

function collectPayload() {
  const age = parseFloat(els.age.value);
  if (!Number.isFinite(age) || age <= 0 || age > 150) {
    throw new Error('请填写有效的年龄（1–150 岁）');
  }
  const gender = segValue(els.genderSeg);
  if (!gender) {
    throw new Error('请选择性别');
  }

  const symptoms = {};
  els.symptomList.querySelectorAll('.seg').forEach((seg) => {
    if (segValue(seg) === '1') symptoms[seg.dataset.symptom] = true;
  });

  const labs = {};
  els.labGrid.querySelectorAll('input[data-lab]').forEach((input) => {
    if (input.value.trim() !== '') {
      const value = Number(input.value);
      if (!Number.isFinite(value)) throw new Error(`检验项目 ${input.dataset.lab} 的结果必须是数值`);
      labs[input.dataset.lab] = value;
    }
  });
  const qual = document.getElementById('qual-lab').value;
  if (qual) labs[QUAL_LAB] = qual;

  return { age, gender, symptoms, labs };
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

async function submitForm(event) {
  event.preventDefault();
  showError('');
  setBusy(true);
  try {
    const payload = collectPayload();
    const threshold = thresholdParam();
    const resp = await fetch(`/api/predict/form?threshold=${threshold}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const data = await parseResponse(resp);
    renderResult(data.patients[0]);
  } catch (err) {
    showError(err.message);
  } finally {
    setBusy(false);
  }
}

function renderResult(patient) {
  const d = patient.detail;
  const badge = patient.label
    ? `<span class="badge ${patient.label === '肺炎' ? 'badge-danger' : 'badge-ok'}">${escapeHtml(patient.label)}</span>`
    : '';
  const symptoms = d.symptoms_positive.length
    ? d.symptoms_positive.map((s) => `<span class="chip">${escapeHtml(s)}</span>`).join('')
    : '<span class="muted">无阳性症状</span>';
  const measuredLabs = d.labs.filter((lab) => lab.measured);
  const labRows = measuredLabs.length
    ? measuredLabs.map((lab) => {
        const result = lab.positive !== null
          ? (lab.positive ? '<span class="badge badge-danger">阳性</span>' : '<span class="badge badge-ok">阴性</span>')
          : formatNum(lab.value);
        return `<tr><td>${escapeHtml(lab.name)}</td><td>${result}</td></tr>`;
      }).join('')
    : '<tr><td colspan="2" class="muted">未填写检验项目</td></tr>';

  els.resultContent.innerHTML = `
    <div class="score-panel">
      <div class="score-number">${patient.score.toFixed(4)}</div>
      <div class="score-side">
        ${badge}
        <p class="muted">年龄 ${d.age ?? '未知'} · ${d.gender ?? '未知'} · 阈值 ${els.threshold.value}</p>
      </div>
    </div>
    <h3>阳性症状</h3>
    <div class="chips">${symptoms}</div>
    <h3>检验结果</h3>
    <div class="table-scroll">
      <table class="labs-table">
        <thead><tr><th>项目</th><th>结果</th></tr></thead>
        <tbody>${labRows}</tbody>
      </table>
    </div>`;
  els.resultSection.hidden = false;
  els.resultSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function fillDemo(demo) {
  resetForm();
  els.age.value = demo.age;
  setSeg(els.genderSeg, demo.gender);
  els.symptomList.querySelectorAll('.seg').forEach((seg) => {
    setSeg(seg, demo.symptoms.includes(seg.dataset.symptom) ? '1' : '0');
  });
  els.labGrid.querySelectorAll('input[data-lab]').forEach((input) => {
    if (demo.labs[input.dataset.lab] !== undefined) input.value = demo.labs[input.dataset.lab];
  });
  document.getElementById('qual-lab').value = demo.qualLab;
  showError('示例已填入，点击「提交评分」查看结果');
  els.errorBox.classList.add('info-box');
}

function resetForm() {
  els.errorBox.classList.remove('info-box');
  showError('');
  els.age.value = '';
  setSeg(els.genderSeg, null);
  els.symptomList.querySelectorAll('.seg').forEach((seg) => setSeg(seg, '0'));
  els.labGrid.querySelectorAll('input[data-lab]').forEach((input) => { input.value = ''; });
  document.getElementById('qual-lab').value = '';
  els.resultSection.hidden = true;
}

function formatNum(value) {
  if (value === null || value === undefined) return '—';
  return Number.isFinite(value) ? Math.round(value * 10000) / 10000 : '—';
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (ch) => (
    { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch]
  ));
}

buildForm();

document.addEventListener('click', (event) => {
  const btn = event.target.closest('.seg-btn');
  if (btn) setSeg(btn.parentElement, btn.dataset.value);
});

els.form.addEventListener('submit', submitForm);
els.demoFy.addEventListener('click', () => fillDemo(DEMO_FY13));
els.resetBtn.addEventListener('click', resetForm);
