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

SYMPTOM_EN_TO_ZH = {en: zh for zh, en in preprocessing.SYMPTOM_NAME_MAP.items()}
LAB_EN_TO_ZH = {en: zh for zh, en in preprocessing.LAB_NAME_MAP.items()}

FORM_PATIENT_ID = "FORM-1"
QUALITATIVE_LAB = "肺炎支原体抗体.IgM"

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


def _form_age_gender(payload: dict) -> tuple[float, str]:
    try:
        age = float(payload.get("age"))
    except (TypeError, ValueError):
        raise ValueError("年龄必填且必须为数值") from None
    if not 0 < age <= 150:
        raise ValueError("年龄必须在 0 到 150 之间")
    gender = payload.get("gender")
    if gender not in {"男", "女"}:
        raise ValueError("性别必填（男/女）")
    return age, gender


def build_form_tables(payload: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Validate the questionnaire JSON and rebuild the raw long tables from it."""
    if not isinstance(payload, dict):
        raise ValueError("请求格式不正确")
    age, gender = _form_age_gender(payload)

    symptoms = payload.get("symptoms") or {}
    if not isinstance(symptoms, dict):
        raise ValueError("症状字段格式不正确")
    unknown_symptoms = sorted(set(symptoms) - set(preprocessing.SYMPTOM_NAME_MAP))
    if unknown_symptoms:
        raise ValueError(f"未登记的症状名称: {unknown_symptoms}")

    labs = payload.get("labs") or {}
    if not isinstance(labs, dict):
        raise ValueError("检验字段格式不正确")
    unknown_labs = sorted(set(labs) - set(preprocessing.LAB_NAME_MAP))
    if unknown_labs:
        raise ValueError(f"未登记的检验项目: {unknown_labs}")

    symptom_table = pd.DataFrame(
        [
            {
                "PatientID": FORM_PATIENT_ID,
                "Gender": gender,
                "Age": age,
                "症状与体征-中文": name,
                "查体结果": "是" if symptoms.get(name) else "否",
            }
            for name in preprocessing.SYMPTOM_NAME_MAP
        ]
    )

    lab_rows = []
    for name, value in labs.items():
        row = {
            "patientId": FORM_PATIENT_ID,
            "gender": gender,
            "age": age,
            "resultDateTime": "",
            "reportDateTime": "",
            "laboratoryName": name,
            "standardResult": "",
            "standardResultNorm": "",
            "standardNormalizedQuantitative": "",
            "abnormal": "",
            "standardResultType": "",
        }
        if name == QUALITATIVE_LAB:
            if value not in {"阳性", "阴性"}:
                raise ValueError(f"{QUALITATIVE_LAB} 只能填 阳性/阴性")
            row["standardResult"] = value
            row["standardResultNorm"] = value
            row["standardResultType"] = "QUALITATIVE"
        else:
            try:
                number = float(value)
            except (TypeError, ValueError):
                raise ValueError(f"检验项目 {name} 的结果必须是数值") from None
            row["standardResult"] = number
            row["standardResultNorm"] = number
            row["standardResultType"] = "QUANTIFY"
        lab_rows.append(row)

    if not lab_rows:
        # preprocessing requires a non-empty lab file; a placeholder row with an
        # unrecognized item name is ignored by the feature builder.
        lab_rows.append(
            {
                "patientId": FORM_PATIENT_ID,
                "gender": gender,
                "age": age,
                "resultDateTime": "",
                "reportDateTime": "",
                "laboratoryName": "",
                "standardResult": "",
                "standardResultNorm": "",
                "standardNormalizedQuantitative": "",
                "abnormal": "",
                "standardResultType": "",
            }
        )
    lab_table = pd.DataFrame(lab_rows)
    return symptom_table, lab_table


def run_form_prediction(payload: dict, threshold: float | None) -> dict[str, Any]:
    symptom_table, lab_table = build_form_tables(payload)
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        symptom_path = tmp / "symptoms.csv"
        lab_path = tmp / "labs.csv"
        symptom_table.to_csv(symptom_path, index=False, encoding="utf-8-sig")
        lab_table.to_csv(lab_path, index=False, encoding="utf-8-sig")
        return run_prediction(symptom_path, lab_path, threshold)
