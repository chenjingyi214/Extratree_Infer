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
        try:
            _MODEL = joblib.load(MODEL_PATH)
        except Exception as exc:
            raise RuntimeError(f"模型文件加载失败: {MODEL_PATH}") from exc
    return _MODEL


def get_feature_names() -> list[str]:
    global _FEATURE_NAMES
    if _FEATURE_NAMES is None:
        try:
            _FEATURE_NAMES = infer.load_feature_names(FEATURE_LIST_PATH)
        except Exception as exc:
            raise RuntimeError(f"特征列表加载失败: {FEATURE_LIST_PATH}") from exc
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
