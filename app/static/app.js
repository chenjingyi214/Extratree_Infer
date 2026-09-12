const I18N = {
  en: {
    docTitle: 'CAP Auxiliary Score · ExtraTrees Inference',
    title: 'Community-Acquired Pneumonia Auxiliary Score',
    subtitle: 'Frozen ExtraTrees model predicting secondary community-acquired pneumonia (pneumonia) following acute upper respiratory infection (common cold) · For research reference only, not a diagnosis',
    langButton: '中文',
    sec1: '1. Basic Information <span class="tag tag-required">Required</span>',
    sec2: '2. Signs & Symptoms <span class="tag tag-optional">Optional · defaults to "No"</span>',
    sec3: '3. Laboratory Tests <span class="tag tag-optional">Optional · leave blank if not tested</span>',
    age: 'Age <i class="req">*</i>',
    agePlaceholder: 'years',
    gender: 'Sex <i class="req">*</i>',
    male: 'Male',
    female: 'Female',
    yes: 'Yes',
    no: 'No',
    derivedHint: 'The three ratios (MLR, NLR, PLR) and two indices (SII, SIRI) are computed automatically from the cell counts — no need to fill them in.',
    threshold: 'Threshold',
    submit: 'Score',
    submitBusy: 'Scoring…',
    demoFy: 'Example · Pneumonia',
    reset: 'Clear',
    notTested: 'Not tested',
    negative: 'Negative',
    positive: 'Positive',
    resultTitle: 'Result',
    positiveSymptoms: 'Positive symptoms',
    noPositiveSymptoms: 'No positive symptoms',
    labResults: 'Lab results',
    item: 'Item',
    result: 'Result',
    noLabs: 'No lab tests provided',
    pneumonia: 'Pneumonia',
    uri: 'URI (cold)',
    metaAge: 'Age',
    thresholdNote: 'threshold',
    unknown: 'Unknown',
    demoFilled: 'Example filled in — click "Score" to see the result',
    errorAge: 'Please enter a valid age (1–150)',
    errorGender: 'Please select sex',
    errorThreshold: 'Threshold must be a number between 0 and 1',
    errorLabNumber: (name) => `The result of ${name} must be numeric`,
    footer: 'The score is an uncalibrated model output. It is not a probability of disease and cannot replace professional medical diagnosis.',
    symptoms: {
      '乏力': 'Fatigue', '低热': 'Slight fever', '呼吸困难': 'Dyspnea',
      '咳嗽': 'Cough', '咳痰': 'Sputum', '喷嚏': 'Sneeze',
      '头晕/疼': 'Dizziness Headache', '憋气': 'Chest tightness',
      '气短': 'Shortness of breath', '流涕': 'Rhinorrhea', '胸痛': 'Thoracalgia',
      '鼻塞': 'Nasal obstruction', '意识模糊/嗜睡': 'Clouding of consciousness/somnolence',
    },
    labs: {
      '白细胞计数': 'WBC', '中性粒细胞计数': 'Neu',
      '淋巴细胞计数': 'LY', '单核细胞计数': 'Mon',
      '血小板计数': 'PLT', '血小板分布宽度': 'PDW',
      '红细胞比容': 'HCT', 'C反应蛋白': 'CRP',
      '淀粉样蛋白A': 'SAA', '肺炎支原体抗体.IgM': 'MP-IgM',
      '单核细胞/淋巴细胞比值': 'MLR',
      '中性粒细胞/淋巴细胞比值': 'NLR',
      '血小板/淋巴细胞比值': 'PLR',
      '系统性免疫炎症指数': 'SII',
      '系统性炎症反应指数': 'SIRI',
    },
  },
  zh: {
    docTitle: '社区获得性肺炎辅助评分 · ExtraTrees 推理',
    title: '社区获得性肺炎辅助评分',
    subtitle: '基于冻结 ExtraTrees 模型预测急性上呼吸道感染（感冒）继发社区获得性肺炎（肺炎）· 结果仅供研究参考，非诊断结论',
    langButton: 'EN',
    sec1: '1. 基本信息 <span class="tag tag-required">必填</span>',
    sec2: '2. 症状与体征 <span class="tag tag-optional">选填 · 默认为「无」</span>',
    sec3: '3. 检验项目 <span class="tag tag-optional">选填 · 没测的项目留空即可</span>',
    age: '年龄 <i class="req">*</i>',
    agePlaceholder: '岁',
    gender: '性别 <i class="req">*</i>',
    male: '男',
    female: '女',
    yes: '有',
    no: '无',
    derivedHint: '三个比值（单核/淋巴、中性粒/淋巴、血小板/淋巴）与两个指数（系统性免疫炎症指数、系统性炎症反应指数）由计数自动计算，无需填写。',
    threshold: '分类阈值',
    submit: '提交评分',
    submitBusy: '评分中…',
    demoFy: '示例·肺炎患者',
    reset: '清空',
    notTested: '未测',
    negative: '阴性',
    positive: '阳性',
    resultTitle: '评分结果',
    positiveSymptoms: '阳性症状',
    noPositiveSymptoms: '无阳性症状',
    labResults: '检验结果',
    item: '项目',
    result: '结果',
    noLabs: '未填写检验项目',
    pneumonia: '肺炎',
    uri: '上感',
    metaAge: '年龄',
    thresholdNote: '阈值',
    unknown: '未知',
    demoFilled: '示例已填入，点击「提交评分」查看结果',
    errorAge: '请填写有效的年龄（1–150 岁）',
    errorGender: '请选择性别',
    errorThreshold: '阈值必须是 0 到 1 之间的数值',
    errorLabNumber: (name) => `检验项目 ${name} 的结果必须是数值`,
    footer: '模型得分为未经校准的输出分数，不能解释为患病概率，也不能替代医生诊断。',
    symptoms: {
      '乏力': '乏力', '低热': '低热', '呼吸困难': '呼吸困难',
      '咳嗽': '咳嗽', '咳痰': '咳痰', '喷嚏': '喷嚏',
      '头晕/疼': '头晕/疼', '憋气': '憋气',
      '气短': '气短', '流涕': '流涕', '胸痛': '胸痛',
      '鼻塞': '鼻塞', '意识模糊/嗜睡': '意识模糊/嗜睡',
    },
    labs: {
      '白细胞计数': '白细胞计数', '中性粒细胞计数': '中性粒细胞计数',
      '淋巴细胞计数': '淋巴细胞计数', '单核细胞计数': '单核细胞计数',
      '血小板计数': '血小板计数', '血小板分布宽度': '血小板分布宽度',
      '红细胞比容': '红细胞比容', 'C反应蛋白': 'C反应蛋白',
      '淀粉样蛋白A': '淀粉样蛋白A', '肺炎支原体抗体.IgM': '肺炎支原体抗体 IgM',
      '单核细胞/淋巴细胞比值': '单核细胞/淋巴细胞比值',
      '中性粒细胞/淋巴细胞比值': '中性粒细胞/淋巴细胞比值',
      '血小板/淋巴细胞比值': '血小板/淋巴细胞比值',
      '系统性免疫炎症指数': '系统性免疫炎症指数',
      '系统性炎症反应指数': '系统性炎症反应指数',
    },
  },
};

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
  langToggle: document.getElementById('lang-toggle'),
  errorBox: document.getElementById('error-box'),
  resultSection: document.getElementById('result-section'),
  resultContent: document.getElementById('result-content'),
};

let currentLang = 'en';
let lastPatient = null;

function t(key) {
  return I18N[currentLang][key];
}

function showError(message, info = false) {
  els.errorBox.classList.toggle('info-box', info);
  els.errorBox.textContent = message || '';
  els.errorBox.hidden = !message;
}

function setBusy(busy) {
  els.submitBtn.disabled = busy;
  els.submitBtn.textContent = busy ? t('submitBusy') : t('submit');
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
      <span class="symptom-name"></span>
      <div class="seg seg-sm" data-symptom="${name}">
        <button type="button" class="seg-btn active" data-value="0"></button>
        <button type="button" class="seg-btn" data-value="1"></button>
      </div>`;
    els.symptomList.appendChild(row);
  });

  QUANT_LABS.forEach((name) => {
    const label = document.createElement('label');
    label.className = 'field lab-field';
    label.innerHTML = `
      <span class="field-label"></span>
      <input type="number" step="any" data-lab="${name}" />`;
    els.labGrid.appendChild(label);
  });

  const qualLabel = document.createElement('label');
  qualLabel.className = 'field lab-field';
  qualLabel.innerHTML = `
    <span class="field-label"></span>
    <select id="qual-lab">
      <option value=""></option>
      <option value="阴性"></option>
      <option value="阳性"></option>
    </select>`;
  els.labGrid.appendChild(qualLabel);
}

function applyLang(lang) {
  currentLang = lang;
  try { localStorage.setItem('cap-lang', lang); } catch (e) { /* ignore */ }
  const d = I18N[lang];
  document.documentElement.lang = lang === 'zh' ? 'zh-CN' : 'en';
  document.title = d.docTitle;
  document.querySelectorAll('[data-i18n]').forEach((el) => { el.textContent = d[el.dataset.i18n]; });
  document.querySelectorAll('[data-i18n-html]').forEach((el) => { el.innerHTML = d[el.dataset.i18nHtml]; });

  els.langToggle.textContent = d.langButton;
  els.age.placeholder = d.agePlaceholder;
  els.genderSeg.querySelectorAll('.seg-btn').forEach((btn) => {
    btn.textContent = btn.dataset.value === '男' ? d.male : d.female;
  });
  els.symptomList.querySelectorAll('.symptom-row').forEach((row) => {
    const seg = row.querySelector('.seg');
    row.querySelector('.symptom-name').textContent = d.symptoms[seg.dataset.symptom];
    const [noBtn, yesBtn] = seg.querySelectorAll('.seg-btn');
    noBtn.textContent = d.no;
    yesBtn.textContent = d.yes;
  });
  els.labGrid.querySelectorAll('input[data-lab]').forEach((input) => {
    input.previousElementSibling.textContent = d.labs[input.dataset.lab];
    input.placeholder = d.notTested;
  });
  const qual = document.getElementById('qual-lab');
  qual.previousElementSibling.textContent = d.labs[QUAL_LAB];
  const [optEmpty, optNeg, optPos] = qual.querySelectorAll('option');
  optEmpty.textContent = d.notTested;
  optNeg.textContent = d.negative;
  optPos.textContent = d.positive;

  if (!els.submitBtn.disabled) els.submitBtn.textContent = d.submit;
  if (lastPatient && !els.resultSection.hidden) renderResult(lastPatient);
}

function collectPayload() {
  const age = parseFloat(els.age.value);
  if (!Number.isFinite(age) || age <= 0 || age > 150) {
    throw new Error(t('errorAge'));
  }
  const gender = segValue(els.genderSeg);
  if (!gender) {
    throw new Error(t('errorGender'));
  }

  const symptoms = {};
  els.symptomList.querySelectorAll('.seg').forEach((seg) => {
    if (segValue(seg) === '1') symptoms[seg.dataset.symptom] = true;
  });

  const labs = {};
  els.labGrid.querySelectorAll('input[data-lab]').forEach((input) => {
    if (input.value.trim() !== '') {
      const value = Number(input.value);
      if (!Number.isFinite(value)) throw new Error(t('errorLabNumber')(input.dataset.lab));
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
    throw new Error(t('errorThreshold'));
  }
  return value;
}

async function parseResponse(resp) {
  const data = await resp.json().catch(() => null);
  if (!resp.ok) {
    const detail = data && data.detail ? data.detail : `Request failed (HTTP ${resp.status})`;
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
  lastPatient = patient;
  const d = I18N[currentLang];
  const labelText = patient.label === '肺炎' ? d.pneumonia : d.uri;
  const badge = patient.label
    ? `<span class="badge ${patient.label === '肺炎' ? 'badge-danger' : 'badge-ok'}">${labelText}</span>`
    : '';
  const genderText = patient.detail.gender === '男' ? d.male : d.female;
  const symptoms = patient.detail.symptoms_positive.length
    ? patient.detail.symptoms_positive.map((s) => `<span class="chip">${escapeHtml(d.symptoms[s] || s)}</span>`).join('')
    : `<span class="muted">${d.noPositiveSymptoms}</span>`;
  const measuredLabs = patient.detail.labs.filter((lab) => lab.measured);
  const labRows = measuredLabs.length
    ? measuredLabs.map((lab) => {
        const result = lab.positive !== null
          ? (lab.positive ? `<span class="badge badge-danger">${d.positive}</span>` : `<span class="badge badge-ok">${d.negative}</span>`)
          : formatNum(lab.value);
        return `<tr><td>${escapeHtml(d.labs[lab.name] || lab.name)}</td><td>${result}</td></tr>`;
      }).join('')
    : `<tr><td colspan="2" class="muted">${d.noLabs}</td></tr>`;

  els.resultContent.innerHTML = `
    <div class="score-panel">
      <div class="score-number">${patient.score.toFixed(4)}</div>
      <div class="score-side">
        ${badge}
        <p class="muted">${d.metaAge} ${patient.detail.age ?? d.unknown} · ${patient.detail.gender ? genderText : d.unknown} · ${d.thresholdNote} ${els.threshold.value}</p>
      </div>
    </div>
    <h3>${d.positiveSymptoms}</h3>
    <div class="chips">${symptoms}</div>
    <h3>${d.labResults}</h3>
    <div class="table-scroll">
      <table class="labs-table">
        <thead><tr><th>${d.item}</th><th>${d.result}</th></tr></thead>
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
  showError(t('demoFilled'), true);
}

function resetForm() {
  showError('');
  els.age.value = '';
  setSeg(els.genderSeg, null);
  els.symptomList.querySelectorAll('.seg').forEach((seg) => setSeg(seg, '0'));
  els.labGrid.querySelectorAll('input[data-lab]').forEach((input) => { input.value = ''; });
  document.getElementById('qual-lab').value = '';
  lastPatient = null;
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
els.langToggle.addEventListener('click', () => applyLang(currentLang === 'zh' ? 'en' : 'zh'));

let initialLang = 'en';
const urlLang = new URLSearchParams(location.search).get('lang');
if (urlLang === 'zh' || urlLang === 'en') {
  initialLang = urlLang;
} else {
  try {
    const saved = localStorage.getItem('cap-lang');
    if (saved === 'zh' || saved === 'en') initialLang = saved;
  } catch (e) { /* ignore */ }
}
applyLang(initialLang);
