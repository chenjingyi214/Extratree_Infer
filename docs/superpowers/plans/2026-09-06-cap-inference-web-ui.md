# CAP ExtraTrees 推理 Web UI 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 ExtraTrees 肺炎推理包新增 FastAPI 后端 + 免构建单页前端，浏览器中完成 CSV 上传、推理、结果与患者详情展示。

**Architecture:** 新增 `app/` 包：`service.py` 直接 import 现有 `preprocessing.py` / `infer.py` 的函数跑流水线并组装患者详情；`main.py` 提供三个 API 端点并托管 `app/static/` 下的单页（HTML + 原生 JS + CSS）。现有两个脚本不改动。

**Tech Stack:** Python 3.11（现有 `.venv`，uv 管理）、FastAPI + Uvicorn、scikit-learn 1.9.0、pandas 2.3.3、原生 HTML/JS/CSS（无 node 构建）。

**Spec:** `docs/superpowers/specs/2026-09-06-cap-inference-web-ui-design.md`

## Global Constraints

- 工作目录为 `Extratree_infer/Extratree_infer`（git 仓库根），所有命令在此目录执行
- Python 解释器固定为 `.venv/bin/python`，安装固定用 `UV_HTTP_TIMEOUT=180 uv pip install --python .venv/bin/python ...`（默认 30s 超时会失败）
- `preprocessing.py` 和 `infer.py` 一行不改，只 import
- requirements.txt 中所有依赖必须 `==` 固定版本
- 上传单个文件 ≤ 20MB；API 的 `threshold` 为可选 query 参数（0–1），未传时响应 `label` 为 `null`（前端始终会传，默认 0.16）
- 验证基准：示例两位患者得分必须为 0.80375（KJSQ-FY-13，肺炎）/ 0.035625（KJSQ-SG-106，上感），误差 ≤ 1e-6
- 页面常驻免责声明：得分为非校准输出，不能替代医生诊断

---

### Task 1: 后端 API（service + main + 测试）

**Files:**
- Modify: `requirements.txt`（追加依赖）
- Create: `app/__init__.py`
- Create: `app/service.py`
- Create: `app/main.py`
- Test: `tests/conftest.py`、`tests/test_api.py`

**Interfaces:**
- Consumes: `preprocessing.run_preprocessing(symptom_input: Path, lab_input: Path, output: Path, feature_list: Path) -> pd.DataFrame`、`preprocessing.SYMPTOM_NAME_MAP` / `LAB_NAME_MAP`（zh→en dict）、`infer.load_feature_names(path) -> list[str]`、`infer.prepare_features(frame, feature_names) -> (pd.DataFrame, pd.Series)`、`infer.positive_scores(model, features) -> np.ndarray`
- Produces（前端 Task 2 依赖的响应 JSON）：
  - `POST /api/predict`（multipart: `symptom_file`, `lab_file`；query: `threshold?`）→ `{ "patients": [{ "patient_id": str, "score": float, "label": "肺炎"|"上感"|null, "detail": { "age": float|null, "gender": "男"|"女"|null, "symptoms_positive": [str], "labs": [{ "name": str, "measured": bool, "value": float|null, "normalized": float|null, "positive": bool|null }] } }] }`
  - `POST /api/predict/demo`（query: `threshold?`）→ 同上结构，额外含 `symptoms_preview` / `labs_preview`：`{ "columns": [str], "rows": [[cell|null]] }`（前 5 行）
  - `GET /api/demo/files/{symptoms|labs}` → CSV 文件下载；未知 kind → 404
  - 业务校验失败 → 400 + `{ "detail": "中文错误消息" }`；模型加载失败 → 500 通用提示
  - `GET /` 及静态文件由 `app/static/` 托管（Task 2 填充内容）

- [ ] **Step 1: 安装并固定新依赖**

```bash
cd Extratree_infer/Extratree_infer
UV_HTTP_TIMEOUT=180 uv pip install --python .venv/bin/python fastapi "uvicorn[standard]" python-multipart pytest httpx
UV_HTTP_TIMEOUT=180 .venv/bin/python -c "import fastapi, uvicorn, multipart, pytest, httpx; print(fastapi.__version__, uvicorn.__version__, pytest.__version__, httpx.__version__)"
```

将 freeze 出的实际版本以 `==` 形式追加到 `requirements.txt` 末尾（fastapi / uvicorn / python-multipart / pytest / httpx，以及 uvicorn[standard] 带入的 uvloop、httptools、websockets、watchfiles、python-dotenv、PyYAML、click、h11、anyio、starlette、idna、sniffio、typing-extensions 等由 uv 自动装，不需要写进 requirements；只写直接依赖五项）：

```bash
.venv/bin/python - <<'EOF'
import importlib.metadata as m
for pkg in ["fastapi", "uvicorn", "python-multipart", "pytest", "httpx"]:
    print(f"{pkg}=={m.version(pkg)}")
EOF
```

把输出的 5 行追加到 `requirements.txt`。

- [ ] **Step 2: 写失败的测试**

创建 `tests/conftest.py`：

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
```

创建 `tests/test_api.py`：

```python
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app

ROOT = Path(__file__).resolve().parent.parent
client = TestClient(app)


def _upload_files():
    return {
        "symptom_file": (
            "test_cases_raw_symptoms.csv",
            (ROOT / "test_cases_raw_symptoms.csv").read_bytes(),
            "text/csv",
        ),
        "lab_file": (
            "test_cases_raw_labs.csv",
            (ROOT / "test_cases_raw_labs.csv").read_bytes(),
            "text/csv",
        ),
    }


def test_demo_returns_reference_scores():
    resp = client.post("/api/predict/demo", params={"threshold": 0.16})
    assert resp.status_code == 200
    data = resp.json()
    scores = {p["patient_id"]: p["score"] for p in data["patients"]}
    assert scores["KJSQ-FY-13"] == pytest.approx(0.80375, abs=1e-6)
    assert scores["KJSQ-SG-106"] == pytest.approx(0.035625, abs=1e-6)
    labels = {p["patient_id"]: p["label"] for p in data["patients"]}
    assert labels == {"KJSQ-FY-13": "肺炎", "KJSQ-SG-106": "上感"}
    assert "PatientID" in data["symptoms_preview"]["columns"]
    assert "patientId" in data["labs_preview"]["columns"]
    assert len(data["symptoms_preview"]["rows"]) <= 5
    detail = next(p for p in data["patients"] if p["patient_id"] == "KJSQ-FY-13")["detail"]
    assert detail["age"] == 91.0
    assert detail["gender"] == "女"
    measured = {lab["name"]: lab["measured"] for lab in detail["labs"]}
    assert measured["白细胞计数"] is True


def test_demo_without_threshold_has_null_labels():
    resp = client.post("/api/predict/demo")
    assert resp.status_code == 200
    assert all(p["label"] is None for p in resp.json()["patients"])


def test_predict_upload_matches_reference():
    resp = client.post("/api/predict", files=_upload_files(), params={"threshold": 0.16})
    assert resp.status_code == 200
    scores = {p["patient_id"]: p["score"] for p in resp.json()["patients"]}
    assert scores["KJSQ-FY-13"] == pytest.approx(0.80375, abs=1e-6)
    assert scores["KJSQ-SG-106"] == pytest.approx(0.035625, abs=1e-6)


def test_predict_rejects_non_csv():
    files = {
        "symptom_file": ("notes.txt", b"hello", "text/plain"),
        "lab_file": ("labs.csv", b"a,b\n1,2\n", "text/csv"),
    }
    resp = client.post("/api/predict", files=files)
    assert resp.status_code == 400


def test_predict_rejects_missing_columns():
    files = {
        "symptom_file": ("symptoms.csv", b"foo,bar\n1,2\n", "text/csv"),
        "lab_file": ("labs.csv", b"foo,bar\n1,2\n", "text/csv"),
    }
    resp = client.post("/api/predict", files=files)
    assert resp.status_code == 400
    assert "缺少必要字段" in resp.json()["detail"]


def test_predict_rejects_out_of_range_threshold():
    resp = client.post("/api/predict", files=_upload_files(), params={"threshold": 1.5})
    assert resp.status_code == 400


def test_demo_file_download():
    resp = client.get("/api/demo/files/symptoms")
    assert resp.status_code == 200
    assert "PatientID" in resp.text
    assert client.get("/api/demo/files/nope").status_code == 404
```

- [ ] **Step 3: 运行测试确认失败**

```bash
cd Extratree_infer/Extratree_infer && .venv/bin/python -m pytest tests/ -x -q
```

预期：收集阶段即失败，`ModuleNotFoundError: No module named 'app'`。

- [ ] **Step 4: 实现后端**

创建 `app/__init__.py`（空文件）。

创建 `app/service.py`：

```python
"""Service layer: run the frozen ExtraTrees pipeline for the web API."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

import joblib
import pandas as pd

import infer
import preprocessing

ROOT = Path(__file__).resolve().parent.parent
MODEL_PATH = ROOT / "extra_trees_sqrt_logloss.joblib"
FEATURE_LIST_PATH = ROOT / "feature_list.json"
DEMO_SYMPTOMS_PATH = ROOT / "test_cases_raw_symptoms.csv"
DEMO_LABS_PATH = ROOT / "test_cases_raw_labs.csv"

SYMPTOM_EN_TO_ZH = {en: zh for zh, en in preprocessing.SYMPTOM_NAME_MAP.items()}
LAB_EN_TO_ZH = {en: zh for zh, en in preprocessing.LAB_NAME_MAP.items()}

_MODEL: Any = None
_FEATURE_NAMES: list[str] | None = None


def get_model() -> Any:
    global _MODEL
    if _MODEL is None:
        if not MODEL_PATH.exists():
            raise RuntimeError(f"模型文件不存在: {MODEL_PATH}")
        _MODEL = joblib.load(MODEL_PATH)
    return _MODEL


def get_feature_names() -> list[str]:
    global _FEATURE_NAMES
    if _FEATURE_NAMES is None:
        _FEATURE_NAMES = infer.load_feature_names(FEATURE_LIST_PATH)
    return _FEATURE_NAMES


def _num(value: Any) -> float | None:
    if value is None or pd.isna(value):
        return None
    return float(value)


def _build_detail(row: pd.Series) -> dict[str, Any]:
    gender_value = row.get("gender_male")
    if gender_value is None or pd.isna(gender_value):
        gender = None
    else:
        gender = "男" if int(gender_value) == 1 else "女"

    symptoms_positive = [
        SYMPTOM_EN_TO_ZH[en]
        for en in SYMPTOM_EN_TO_ZH
        if row.get(f"symptom_{en}") == 1
    ]

    labs = []
    for en in sorted(LAB_EN_TO_ZH):
        positive = _num(row.get(f"lab_positive_{en}"))
        labs.append(
            {
                "name": LAB_EN_TO_ZH[en],
                "measured": bool(row.get(f"lab_measured_{en}", 0)),
                "value": _num(row.get(f"lab_value_{en}")),
                "normalized": _num(row.get(f"lab_normalized_{en}")),
                "positive": None if positive is None else bool(positive),
            }
        )

    return {
        "age": _num(row.get("age")),
        "gender": gender,
        "symptoms_positive": symptoms_positive,
        "labs": labs,
    }


def run_prediction(
    symptom_path: Path, lab_path: Path, threshold: float | None
) -> dict[str, Any]:
    feature_names = get_feature_names()
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "features.csv"
        features = preprocessing.run_preprocessing(
            symptom_path, lab_path, output_path, FEATURE_LIST_PATH
        )
    numeric, patient_ids = infer.prepare_features(features, feature_names)
    scores = infer.positive_scores(get_model(), numeric)

    indexed = features.set_index("patient_id")
    patients = []
    for patient_id, score in zip(patient_ids, scores):
        label = None
        if threshold is not None:
            label = "肺炎" if score >= threshold else "上感"
        patients.append(
            {
                "patient_id": str(patient_id),
                "score": float(score),
                "label": label,
                "detail": _build_detail(indexed.loc[str(patient_id)]),
            }
        )
    return {"patients": patients}


def csv_preview(path: Path, max_rows: int = 5) -> dict[str, Any]:
    frame = pd.read_csv(path, encoding="utf-8-sig", nrows=max_rows)
    rows = frame.astype(object).where(frame.notna(), None).values.tolist()
    return {"columns": [str(c) for c in frame.columns], "rows": rows}


def run_demo(threshold: float | None) -> dict[str, Any]:
    result = run_prediction(DEMO_SYMPTOMS_PATH, DEMO_LABS_PATH, threshold)
    result["symptoms_preview"] = csv_preview(DEMO_SYMPTOMS_PATH)
    result["labs_preview"] = csv_preview(DEMO_LABS_PATH)
    return result
```

创建 `app/main.py`：

```python
"""FastAPI entry point for the CAP ExtraTrees web UI."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app import service

MAX_UPLOAD_BYTES = 20 * 1024 * 1024
STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI(title="CAP ExtraTrees 推理服务")


def _validate_threshold(threshold: float | None) -> float | None:
    if threshold is not None and not 0 <= threshold <= 1:
        raise HTTPException(status_code=400, detail="threshold 必须在 0 到 1 之间")
    return threshold


async def _save_upload(upload: UploadFile, directory: Path, field_name: str) -> Path:
    filename = upload.filename or ""
    if not filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail=f"{field_name} 必须是 CSV 文件")
    content = await upload.read()
    if not content:
        raise HTTPException(status_code=400, detail=f"{field_name} 内容为空")
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail=f"{field_name} 超过 20MB 限制")
    path = directory / f"{field_name}.csv"
    path.write_bytes(content)
    return path


def _run_or_400(func, *args):
    try:
        return func(*args)
    except HTTPException:
        raise
    except (ValueError, FileNotFoundError, OSError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail="模型加载失败，请联系管理员") from exc


@app.post("/api/predict")
async def predict(
    symptom_file: UploadFile,
    lab_file: UploadFile,
    threshold: float | None = Query(default=None),
):
    threshold = _validate_threshold(threshold)
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        symptom_path = await _save_upload(symptom_file, tmp, "symptom_file")
        lab_path = await _save_upload(lab_file, tmp, "lab_file")
        return _run_or_400(service.run_prediction, symptom_path, lab_path, threshold)


@app.post("/api/predict/demo")
async def predict_demo(threshold: float | None = Query(default=None)):
    threshold = _validate_threshold(threshold)
    return _run_or_400(service.run_demo, threshold)


@app.get("/api/demo/files/{kind}")
async def demo_file(kind: str):
    paths = {"symptoms": service.DEMO_SYMPTOMS_PATH, "labs": service.DEMO_LABS_PATH}
    path = paths.get(kind)
    if path is None:
        raise HTTPException(status_code=404, detail="未知的示例文件类型")
    return FileResponse(path, media_type="text/csv", filename=path.name)


app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
```

同时创建占位 `app/static/index.html`（Task 2 会替换为完整页面，此处保证 StaticFiles 挂载目录存在）：

```html
<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8"><title>CAP</title></head>
<body>placeholder</body></html>
```

- [ ] **Step 5: 运行测试确认全部通过**

```bash
cd Extratree_infer/Extratree_infer && .venv/bin/python -m pytest tests/ -q
```

预期：7 个测试全部 PASS（首次跑会加载 800 棵树的模型，需数十秒）。

- [ ] **Step 6: 提交**

```bash
cd Extratree_infer/Extratree_infer
git add requirements.txt app tests
git commit -m "feat: 新增 FastAPI 推理服务与 API 测试"
```

---

### Task 2: 前端单页（index.html / style.css / app.js）

**Files:**
- Create（覆盖占位）: `app/static/index.html`
- Create: `app/static/style.css`
- Create: `app/static/app.js`

**Interfaces:**
- Consumes: Task 1 的 `POST /api/predict`、`POST /api/predict/demo`、`GET /api/demo/files/{symptoms|labs}` 响应结构（见 Task 1 Interfaces 块）
- Produces: 无（终端任务）

- [ ] **Step 1: 写 index.html（覆盖占位文件）**

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>肺炎辅助评分 · ExtraTrees 推理</title>
  <link rel="stylesheet" href="/style.css" />
</head>
<body>
  <header class="site-header">
    <h1>肺炎辅助评分</h1>
    <p class="subtitle">基于冻结 ExtraTrees 模型的肺炎 / 上感二分类评分 · 结果仅供研究参考，非诊断结论</p>
  </header>

  <main>
    <section class="card" id="input-card">
      <h2>1. 上传原始数据</h2>
      <div class="upload-row">
        <div class="dropzone" id="symptom-zone">
          <input type="file" id="symptom-file" accept=".csv" hidden />
          <span class="dropzone-icon">📄</span>
          <span class="dropzone-label">症状长表 CSV</span>
          <span class="dropzone-file" id="symptom-name">点击选择或拖入文件</span>
        </div>
        <div class="dropzone" id="lab-zone">
          <input type="file" id="lab-file" accept=".csv" hidden />
          <span class="dropzone-icon">🧪</span>
          <span class="dropzone-label">检验长表 CSV</span>
          <span class="dropzone-file" id="lab-name">点击选择或拖入文件</span>
        </div>
      </div>
      <div class="controls">
        <label class="threshold-field">
          分类阈值
          <input type="number" id="threshold" min="0" max="1" step="0.01" value="0.16" />
        </label>
        <button id="analyze-btn" class="btn btn-primary" type="button">开始分析</button>
        <button id="demo-btn" class="btn btn-ghost" type="button">载入示例数据</button>
      </div>
      <p id="error-box" class="error-box" hidden></p>
    </section>

    <section class="card" id="preview-section" hidden>
      <h2>示例数据格式预览（前 5 行）</h2>
      <div class="preview-grid">
        <div>
          <div class="preview-title">
            <h3>症状长表</h3>
            <a href="/api/demo/files/symptoms" download>下载 CSV</a>
          </div>
          <div class="table-scroll"><table id="symptoms-preview"></table></div>
        </div>
        <div>
          <div class="preview-title">
            <h3>检验长表</h3>
            <a href="/api/demo/files/labs" download>下载 CSV</a>
          </div>
          <div class="table-scroll"><table id="labs-preview"></table></div>
        </div>
      </div>
    </section>

    <section class="card" id="results-section" hidden>
      <div class="results-header">
        <h2>2. 推理结果</h2>
        <button id="export-btn" class="btn btn-ghost" type="button">导出预测 CSV</button>
      </div>
      <table class="results-table">
        <thead>
          <tr>
            <th>患者 ID</th>
            <th class="sortable" id="score-sort">得分 ↓</th>
            <th>判断</th>
          </tr>
        </thead>
        <tbody id="results-body"></tbody>
      </table>
      <p class="hint">点击任意行查看患者特征详情</p>
    </section>
  </main>

  <aside id="drawer" class="drawer" hidden>
    <div class="drawer-panel">
      <button id="drawer-close" class="drawer-close" type="button">×</button>
      <div id="drawer-content"></div>
    </div>
  </aside>

  <footer class="site-footer">
    模型得分为未经校准的输出分数，不能解释为患病概率，也不能替代医生诊断。
  </footer>

  <script src="/app.js"></script>
</body>
</html>
```

- [ ] **Step 2: 写 style.css**

```css
:root {
  --primary: #0f766e;
  --primary-dark: #115e59;
  --bg: #f4f7f8;
  --card: #ffffff;
  --text: #1f2933;
  --muted: #6b7280;
  --danger: #b91c1c;
  --danger-bg: #fee2e2;
  --ok: #15803d;
  --ok-bg: #dcfce7;
  --border: #e2e8f0;
}

* { box-sizing: border-box; }

body {
  margin: 0;
  font-family: -apple-system, "PingFang SC", "Microsoft YaHei", "Helvetica Neue", sans-serif;
  background: var(--bg);
  color: var(--text);
}

.site-header { padding: 2.5rem 1.5rem 1rem; text-align: center; }
.site-header h1 { margin: 0; font-size: 1.75rem; color: var(--primary-dark); }
.subtitle { color: var(--muted); margin: 0.5rem 0 0; }

main { max-width: 960px; margin: 0 auto; padding: 1rem 1.5rem 3rem; display: grid; gap: 1.5rem; }

.card {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 1.5rem;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06);
}
.card h2 { margin: 0 0 1rem; font-size: 1.1rem; }

.upload-row { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
@media (max-width: 640px) { .upload-row { grid-template-columns: 1fr; } }

.dropzone {
  border: 2px dashed var(--border);
  border-radius: 10px;
  padding: 1.5rem 1rem;
  text-align: center;
  cursor: pointer;
  display: grid;
  gap: 0.35rem;
  transition: border-color 0.15s, background 0.15s;
}
.dropzone:hover, .dropzone.dragover { border-color: var(--primary); background: #f0fdfa; }
.dropzone-icon { font-size: 1.5rem; }
.dropzone-label { font-weight: 600; }
.dropzone-file { color: var(--muted); font-size: 0.85rem; word-break: break-all; }

.controls { display: flex; align-items: center; gap: 0.75rem; margin-top: 1.25rem; flex-wrap: wrap; }
.threshold-field { display: flex; align-items: center; gap: 0.5rem; color: var(--muted); font-size: 0.9rem; }
.threshold-field input { width: 5rem; padding: 0.45rem 0.6rem; border: 1px solid var(--border); border-radius: 8px; }

.btn { border-radius: 8px; padding: 0.55rem 1.2rem; font-size: 0.95rem; cursor: pointer; border: 1px solid transparent; }
.btn-primary { background: var(--primary); color: #fff; }
.btn-primary:hover { background: var(--primary-dark); }
.btn-primary:disabled { opacity: 0.6; cursor: wait; }
.btn-ghost { background: #fff; border-color: var(--border); color: var(--primary-dark); }
.btn-ghost:hover { border-color: var(--primary); }

.error-box { margin: 1rem 0 0; padding: 0.75rem 1rem; background: var(--danger-bg); color: var(--danger); border-radius: 8px; font-size: 0.9rem; }

.preview-grid { display: grid; gap: 1.25rem; }
.preview-title { display: flex; justify-content: space-between; align-items: baseline; }
.preview-title h3 { margin: 0 0 0.5rem; font-size: 0.95rem; }
.preview-title a { color: var(--primary); font-size: 0.85rem; }

.table-scroll { overflow-x: auto; }
table { border-collapse: collapse; width: 100%; font-size: 0.85rem; }
th, td { border: 1px solid var(--border); padding: 0.45rem 0.6rem; text-align: left; white-space: nowrap; }
th { background: #f8fafc; font-weight: 600; }

.results-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; }
.results-header h2 { margin: 0; }
.results-table th.sortable { cursor: pointer; user-select: none; }
.results-table tbody tr { cursor: pointer; }
.results-table tbody tr:hover { background: #f0fdfa; }
.score { font-variant-numeric: tabular-nums; font-weight: 600; }
.hint { color: var(--muted); font-size: 0.8rem; margin: 0.75rem 0 0; }

.badge { display: inline-block; padding: 0.15rem 0.6rem; border-radius: 999px; font-size: 0.8rem; }
.badge-danger { background: var(--danger-bg); color: var(--danger); }
.badge-ok { background: var(--ok-bg); color: var(--ok); }
.badge-muted { background: #e5e7eb; color: var(--muted); }

.drawer { position: fixed; inset: 0; background: rgba(15, 23, 42, 0.4); z-index: 10; }
.drawer-panel {
  position: absolute; top: 0; right: 0; bottom: 0;
  width: min(480px, 92vw);
  background: #fff; padding: 1.75rem; overflow-y: auto;
  box-shadow: -4px 0 16px rgba(15, 23, 42, 0.15);
}
.drawer-close { position: absolute; top: 0.75rem; right: 1rem; border: none; background: none; font-size: 1.5rem; cursor: pointer; color: var(--muted); }
.drawer-score { color: var(--muted); }
.drawer-score strong { color: var(--primary-dark); font-size: 1.25rem; }
.chips { display: flex; flex-wrap: wrap; gap: 0.4rem; }
.chip { background: #f0fdfa; color: var(--primary-dark); border: 1px solid #99f6e4; padding: 0.2rem 0.65rem; border-radius: 999px; font-size: 0.8rem; }
.muted, .muted-row td { color: var(--muted); }
.drawer h3 { font-size: 0.95rem; margin: 1.25rem 0 0.5rem; }

.site-footer { text-align: center; color: var(--muted); font-size: 0.8rem; padding: 1.5rem; border-top: 1px solid var(--border); }
```

- [ ] **Step 3: 写 app.js**

```javascript
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
      ? `<span class="badge ${patient.label === '肺炎' ? 'badge-danger' : 'badge-ok'}">${patient.label}</span>`
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
    <p class="drawer-score">得分 <strong>${patient.score.toFixed(4)}</strong>${patient.label ? ` · ${patient.label}` : ''}</p>
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
  const lines = lastPatients.map((p) => `${p.patient_id},${p.score},${p.label ?? ''}`);
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
```

- [ ] **Step 4: 起服务用 curl 验证静态页与接口**

```bash
cd Extratree_infer/Extratree_infer
.venv/bin/uvicorn app.main:app --port 8000 &
sleep 3
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/            # 期望 200
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/app.js      # 期望 200
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/style.css   # 期望 200
curl -s -X POST "http://127.0.0.1:8000/api/predict/demo?threshold=0.16" | .venv/bin/python -c "import json,sys; d=json.load(sys.stdin); print([(p['patient_id'], round(p['score'],6), p['label']) for p in d['patients']])"
# 期望: [('KJSQ-FY-13', 0.80375, '肺炎'), ('KJSQ-SG-106', 0.035625, '上感')]
curl -s -X POST "http://127.0.0.1:8000/api/predict?threshold=0.16" -F "symptom_file=@test_cases_raw_symptoms.csv" -F "lab_file=@test_cases_raw_labs.csv" | .venv/bin/python -c "import json,sys; d=json.load(sys.stdin); print([(p['patient_id'], round(p['score'],6), p['label']) for p in d['patients']])"
# 期望: 同上
kill %1
```

- [ ] **Step 5: 提交**

```bash
cd Extratree_infer/Extratree_infer
git add app/static
git commit -m "feat: 新增免构建单页前端（上传、示例预览、结果表格、患者详情抽屉）"
```

---

### Task 3: 端到端验证与收尾

**Files:**
- Modify: `README.md`（追加 Web UI 使用说明一节）

- [ ] **Step 1: 全量测试 + 端到端 smoke**

```bash
cd Extratree_infer/Extratree_infer
.venv/bin/python -m pytest tests/ -q
.venv/bin/uvicorn app.main:app --port 8000 &
sleep 3
curl -s -X POST "http://127.0.0.1:8000/api/predict/demo?threshold=0.16" | .venv/bin/python -m json.tool | head -20
kill %1
```

确认得分与 `test_cases_reference.csv` 一致（0.80375 / 0.035625，误差 ≤ 1e-6）。

- [ ] **Step 2: README 追加 Web UI 章节**

在 `README.md` 末尾（"## 6. 安全与方法学限制"一节之后）追加以下内容（注意内含一个 bash 代码围栏，原样保留）：

````markdown

## 7. Web 界面（可选）

安装依赖后启动本地服务：

```bash
.venv/bin/uvicorn app.main:app --port 8000
```

浏览器打开 http://127.0.0.1:8000 即可上传症状/检验 CSV 并查看每位患者的得分与特征详情；
"载入示例数据"按钮使用内置样例并展示输入 CSV 的格式预览。Web 层只调用
`preprocessing.py` 与 `infer.py` 的既有逻辑，不改变模型行为。
````

- [ ] **Step 3: 提交**

```bash
cd Extratree_infer/Extratree_infer
git add README.md
git commit -m "docs: README 追加 Web 界面使用说明"
```
