**English** | [简体中文](README_zh.md)

# ExtraTrees Standalone Preprocessing & Inference Package

This directory runs a two-step pipeline end to end: it first converts raw symptom and laboratory long tables into the 58 features the model expects, then scores the pneumonia class with frozen ExtraTrees weights.

The model performs binary classification: `target=1` is pneumonia and `target=0` is acute upper respiratory tract infection (URTI). The output `pneumonia_score` is a model score — not a calibrated clinical probability — and cannot replace a physician's diagnosis.

## Contents

| File | Purpose |
| --- | --- |
| `preprocessing.py` | Converts raw symptom and lab long tables into a patient-level 58-feature CSV |
| `infer.py` | Reads the 58-feature CSV and runs the frozen ExtraTrees model |
| `extra_trees_sqrt_logloss.joblib` | Production ExtraTrees pipeline weights (800 trees) |
| `feature_list.json` | The 58 features the model expects, in fixed order |
| `feature_name_mapping.csv` | Chinese meaning, source, and encoding rules of the 58 features |
| `test_cases_raw_symptoms.csv` | Raw symptom records of two patients drawn from the test set |
| `test_cases_raw_labs.csv` | Raw lab records of the same two patients |
| `test_cases_reference.csv` | Example provenance, true labels, and expected scores; for verification only |
| `requirements.txt` | Python dependency versions compatible with the current weights |
| `app/` | FastAPI backend + questionnaire-style single-page frontend (Web UI, see "Quick start") |
| `tests/` | pytest tests for the Web API |

## Quick start (Web UI)

Requires 64-bit Python 3.11. [uv](https://docs.astral.sh/uv/) is recommended for creating the environment:

```bash
cd Extratree_infer
uv venv --python 3.11 .venv
UV_HTTP_TIMEOUT=180 uv pip install --python .venv/bin/python -r requirements.txt
```

(Alternatively use standard venv + pip as in Section 1. Dependency versions must stay pinned, otherwise the model weights may fail to load or results may drift.)

Start the server:

```bash
.venv/bin/uvicorn app.main:app --port 8000
```

Open **http://127.0.0.1:8000** in a browser, fill in the patient questionnaire, and submit.
The page is in English by default; click the "中文 / EN" button in the top-right corner to
switch languages, or pass `?lang=zh` / `?lang=en` directly:

- **Required**: age, gender
- **Optional**: 13 symptoms (default "no") and 10 lab items (leave blank if not measured —
  the model's built-in rules impute them). The three ratios — monocyte/lymphocyte (MLR),
  neutrophil/lymphocyte (NLR), platelet/lymphocyte (PLR) — and the two indices (SII, SIRI)
  do not need to be entered: they are derived automatically from the base counts using the
  training-data formulas
- The "Example · pneumonia patient" button fills in sample data and submits in one click

Stop the server: press `Ctrl+C` in the terminal.

Run the tests (optional):

```bash
.venv/bin/python -m pytest tests/ -q
```

Sections 1–6 document the command-line (CLI) usage and data formats; the Web UI does not change any of that behavior.

Data flow:

```text
raw symptom CSV + raw lab CSV
              |
              v
      preprocessing.py
              |
              v
 preprocessed_features.csv (58 features)
              |
              v
          infer.py
              |
              v
   pneumonia-class model score
```

## 1. Environment setup

Use 64-bit Python 3.11. The weights were saved under Python 3.11 and scikit-learn 1.9.0; to avoid joblib deserialization failures or result drift, use the pinned versions in `requirements.txt`.

### macOS / Linux

```bash
cd Extratree_infer
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### Windows PowerShell

```powershell
cd Extratree_infer
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Check the versions:

```bash
python --version
python -c "import joblib, numpy, pandas, sklearn, scipy; print(joblib.__version__, numpy.__version__, pandas.__version__, sklearn.__version__, scipy.__version__)"
```

## 2. Run the two bundled raw examples

Preprocessing must run before inference.

### Step 1: raw data → 58 features

Run directly:

```bash
python preprocessing.py
```

Reads by default:

- `test_cases_raw_symptoms.csv`
- `test_cases_raw_labs.csv`

Writes by default:

- `preprocessed_features.csv`

On success it prints (in Chinese):

```text
已写入: .../preprocessed_features.csv（2 位患者，58 个特征）
```

### Step 2: run ExtraTrees inference

```bash
python infer.py
```

`infer.py` reads the `preprocessed_features.csv` produced in the previous step by default and prints the results to the terminal. The output should be close to:

```text
patient_id,pneumonia_score
KJSQ-FY-13,0.80375
KJSQ-SG-106,0.035625
```

Save the predictions:

```bash
python infer.py --output predictions.csv
```

Specify input/output paths for both steps explicitly:

```bash
python preprocessing.py \
  --symptom-input test_cases_raw_symptoms.csv \
  --lab-input test_cases_raw_labs.csv \
  --output test_cases_features.csv

python infer.py \
  --input test_cases_features.csv \
  --output predictions.csv
```

Show all options:

```bash
python preprocessing.py --help
python infer.py --help
```

## 3. Prepare your own raw input

The preprocessor accepts two UTF-8 CSV long tables. Each row is one symptom or lab record; a patient may have many rows. The two tables are merged on patient ID, and each patient ends up as a single output row.

### 3.1 Symptom CSV required fields

| Field | Meaning and allowed values |
| --- | --- |
| `PatientID` | Unique patient identifier; must not be empty |
| `Gender` | `男/女`, `male/female`, `m/f`, or `1/0` |
| `Age` | Age in years; must be convertible to a number |
| `症状与体征-中文` | Raw symptom name (Chinese, see below) |
| `查体结果` | `是/否`, `有/无`, `阳性/阴性`, `1/0`, `true/false`, etc. |

The 13 supported symptom names (the CSV value must be the Chinese name exactly):

| CSV value | English |
| --- | --- |
| 乏力 | Fatigue |
| 低热 | Slight fever |
| 呼吸困难 | Dyspnea |
| 咳嗽 | Cough |
| 咳痰 | Sputum |
| 喷嚏 | Sneeze |
| 头晕/疼 | Dizziness Headache |
| 憋气 | Chest tightness |
| 气短 | Shortness of breath |
| 流涕 | Rhinorrhea |
| 胸痛 | Thoracalgia |
| 鼻塞 | Nasal obstruction |
| 意识模糊/嗜睡 | Clouding of consciousness/somnolence |

When the same patient has several records for the same symptom, the maximum is taken — the symptom is `1` if any record is positive. A missing symptom row or a blank result counts as `0`. Three system-level summary features are generated as the maximum of their member symptoms:

- Respiratory: Cough, Sputum, Dyspnea, Chest tightness, Shortness of breath, Thoracalgia.
- Upper airway: Sneeze, Rhinorrhea, Nasal obstruction.
- Systemic: Fatigue, Slight fever, Dizziness Headache, Clouding of consciousness/somnolence.

The `Hospital` and `Target` columns in the examples are extra fields from the original test set; neither preprocessing nor inference uses them.

### 3.2 Lab CSV required fields

| Field | Meaning |
| --- | --- |
| `patientId` | Patient identifier, matching `PatientID` in the symptom table |
| `gender` | Gender; same encoding rules as the symptom table |
| `age` | Age in years |
| `resultDateTime` | Result time; may be empty |
| `reportDateTime` | Report time; may be empty; preferred for record ordering |
| `laboratoryName` | Standard lab item name |
| `standardResult` | Standardized result; fallback numeric source for quantitative results |
| `standardResultNorm` | Standardized result; numeric value preferred for quantitative items, used to judge positive/negative for qualitative ones |
| `standardNormalizedQuantitative` | Quantitative result normalized against the reference range; may be empty |
| `abnormal` | Abnormality flag; fallback when a qualitative result cannot be interpreted |
| `standardResultType` | `QUANTIFY` or `QUALITATIVE` |

The model uses exactly these 15 lab items (the CSV value must be the Chinese name exactly):

| CSV value | English |
| --- | --- |
| C反应蛋白 | CRP (C-reactive protein) |
| 红细胞比容 | HCT (hematocrit) |
| 淋巴细胞计数 | LY (lymphocyte count) |
| 单核细胞计数 | Mon (monocyte count) |
| 单核细胞/淋巴细胞比值 | MLR (monocyte/lymphocyte ratio) |
| 肺炎支原体抗体.IgM | MP-IgM (Mycoplasma pneumoniae antibody IgM) |
| 中性粒细胞计数 | Neu (neutrophil count) |
| 中性粒细胞/淋巴细胞比值 | NLR (neutrophil/lymphocyte ratio) |
| 血小板计数 | PLT (platelet count) |
| 血小板分布宽度 | PDW (platelet distribution width) |
| 血小板/淋巴细胞比值 | PLR (platelet/lymphocyte ratio) |
| 淀粉样蛋白A | SAA (serum amyloid A) |
| 系统性免疫炎症指数 | SII (systemic immune-inflammation index) |
| 系统性炎症反应指数 | SIRI (systemic inflammation response index) |
| 白细胞计数 | WBC (white blood cell count) |

Other lab items may stay in the raw CSV; the preprocessor ignores them. For each patient and each model lab item, only the latest valid record is kept: records are ordered by `reportDateTime` first (falling back to `resultDateTime`), and ties keep the record that appears later in the file.

Lab feature encoding rules:

| Feature group | Rule |
| --- | --- |
| `lab_measured_*` | `1` if a valid lab record exists, `0` otherwise |
| `lab_value_*` | For quantitative records, prefer the numeric value of `standardResultNorm`, then that of `standardResult` |
| `lab_normalized_*` | Takes `standardNormalizedQuantitative` |
| `lab_positive_*` | `1` for a positive qualitative result, `0` for negative; empty if undeterminable or unmeasured |

Deployment reuses the 15 lab items and the 58-column order fixed at training time. The script does not recompute the "lab missingness ≤ 40%" selection rule on new data — otherwise different batches would produce different model input structures.

### 3.3 Run your own data

```bash
python preprocessing.py \
  --symptom-input my_raw_symptoms.csv \
  --lab-input my_raw_labs.csv \
  --output my_features.csv

python infer.py \
  --input my_features.csv \
  --output my_predictions.csv
```

Missing values in the preprocessing output are kept empty. Do not impute them yourself with means, zeros, or any other rule outside the model, because the saved pipeline already includes:

```text
SimpleImputer(strategy="median", add_indicator=True)
-> VarianceThreshold(threshold=0)
-> ExtraTreesClassifier(criterion="log_loss", n_estimators=800, max_features="sqrt")
```

## 4. Optional classification threshold

By default only the model score is printed. To convert scores into labels you must pass a threshold explicitly, for example:

```bash
python infer.py \
  --input preprocessed_features.csv \
  --threshold 0.16 \
  --output predictions_with_label.csv
```

The output gains:

```text
threshold,predicted_label,predicted_class
0.16,1,肺炎
0.16,0,上感
```

(`肺炎` = pneumonia, `上感` = URTI.) The project once selected `0.16` via the Youden index on the full internal test set, but that threshold is not an independently validated clinical recommendation. No threshold is set by default, to avoid misreading the model score as a direct diagnosis.

## 5. Example provenance and reproduction check

Both raw examples come from the production model's `external_test_kjsq`, with `included_in_training=False`:

| patient_id | True label | Expected score |
| --- | ---: | ---: |
| `KJSQ-FY-13` | 1 (pneumonia) | 0.80375 |
| `KJSQ-SG-106` | 0 (URTI) | 0.035625 |

`test_cases_reference.csv` is for manual verification only; preprocessing and inference never read the true labels. With the same dependency versions and weights, scores should match the table above to within 6 decimal places.

## 6. Security and methodological limitations

- `joblib.load` deserializes Python objects; only load a trusted `extra_trees_sqrt_logloss.joblib`.
- The ExtraTrees outputs are not probability-calibrated; `pneumonia_score=0.8` must not be read as "80% probability of disease".
- This package does not re-clean lab results from raw hospital units and reference ranges, and it does not include retraining, model calibration, clinical decision support, or data de-identification.

## 7. Web UI (optional)

After installing the dependencies, start the local server:

```bash
.venv/bin/uvicorn app.main:app --port 8000
```

Open http://127.0.0.1:8000 to enter a single patient's data in a questionnaire-style form and view the score: age and gender are required; symptoms default to "no"; unmeasured lab items may be left blank (imputed by the model's built-in median). The "Example · pneumonia patient / Example · URTI patient" buttons fill in sample data in one click. The web layer rebuilds the form content into symptom/lab long tables and then calls the existing logic of `preprocessing.py` and `infer.py`; it does not change model behavior.

Note: the form only collects raw lab values; the normalized column (`standardNormalizedQuantitative`) from the original CSV is empty on the form path and is imputed by the model. The example patients therefore score 0.7125 / 0.155 via the form, versus the Section 5 CSV-path reference scores of 0.80375 / 0.035625 — both are correct outputs for their respective inputs.
