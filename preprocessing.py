"""Convert raw symptom/laboratory tables into the frozen 58-feature model input."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


HERE = Path(__file__).resolve().parent
DEFAULT_FEATURE_LIST = HERE / "feature_list.json"
DEFAULT_SYMPTOM_INPUT = HERE / "test_cases_raw_symptoms.csv"
DEFAULT_LAB_INPUT = HERE / "test_cases_raw_labs.csv"
DEFAULT_OUTPUT = HERE / "preprocessed_features.csv"

SYMPTOM_COLUMNS = {
    "patient_id": "PatientID",
    "gender": "Gender",
    "age": "Age",
    "name": "症状与体征-中文",
    "result": "查体结果",
}

LAB_COLUMNS = {
    "patient_id": "patientId",
    "gender": "gender",
    "age": "age",
    "result_time": "resultDateTime",
    "report_time": "reportDateTime",
    "name": "laboratoryName",
    "standard_result": "standardResult",
    "standard_result_norm": "standardResultNorm",
    "standard_normalized_quantitative": "standardNormalizedQuantitative",
    "abnormal": "abnormal",
    "result_type": "standardResultType",
}

SYMPTOM_NAME_MAP = {
    "乏力": "fatigue",
    "低热": "low_grade_fever",
    "呼吸困难": "dyspnea",
    "咳嗽": "cough",
    "咳痰": "sputum_production",
    "喷嚏": "sneezing",
    "头晕/疼": "dizziness_or_headache",
    "憋气": "air_hunger",
    "气短": "shortness_of_breath",
    "流涕": "rhinorrhea",
    "胸痛": "chest_pain",
    "鼻塞": "nasal_congestion",
    "意识模糊/嗜睡": "confusion_or_somnolence",
}

SYMPTOM_SYSTEMS = {
    "respiratory": ["咳嗽", "咳痰", "呼吸困难", "憋气", "气短", "胸痛"],
    "upper_airway": ["喷嚏", "流涕", "鼻塞"],
    "systemic": ["乏力", "低热", "头晕/疼", "意识模糊/嗜睡"],
}

# These are the laboratory items retained when the model was trained.  The
# deployment input must not re-run the training-cohort missingness filter.
LAB_NAME_MAP = {
    "C反应蛋白": "c_reactive_protein",
    "红细胞比容": "hematocrit",
    "淋巴细胞计数": "lymphocyte_count",
    "单核细胞计数": "monocyte_count",
    "单核细胞/淋巴细胞比值": "monocyte_to_lymphocyte_ratio",
    "肺炎支原体抗体.IgM": "mycoplasma_pneumoniae_igm_antibody",
    "中性粒细胞计数": "neutrophil_count",
    "中性粒细胞/淋巴细胞比值": "neutrophil_to_lymphocyte_ratio",
    "血小板计数": "platelet_count",
    "血小板分布宽度": "platelet_distribution_width",
    "血小板/淋巴细胞比值": "platelet_to_lymphocyte_ratio",
    "淀粉样蛋白A": "serum_amyloid_a",
    "系统性免疫炎症指数": "systemic_immune_inflammation_index",
    "系统性炎症反应指数": "systemic_inflammation_response_index",
    "白细胞计数": "white_blood_cell_count",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="将症状长表和检验长表转换为 ExtraTrees 所需的 58 个特征。"
    )
    parser.add_argument(
        "--symptom-input",
        type=Path,
        default=DEFAULT_SYMPTOM_INPUT,
        help="原始症状 CSV（默认：test_cases_raw_symptoms.csv）。",
    )
    parser.add_argument(
        "--lab-input",
        type=Path,
        default=DEFAULT_LAB_INPUT,
        help="原始检验 CSV（默认：test_cases_raw_labs.csv）。",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="输出的58特征 CSV（默认：preprocessed_features.csv）。",
    )
    parser.add_argument("--feature-list", type=Path, default=DEFAULT_FEATURE_LIST)
    return parser.parse_args()


def load_feature_names(path: Path) -> list[str]:
    if not path.exists():
        raise FileNotFoundError(f"特征清单不存在: {path}")
    names = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(names, list) or not all(isinstance(name, str) for name in names):
        raise ValueError("特征清单必须是字符串列表")
    if len(names) != 58 or len(names) != len(set(names)):
        raise ValueError("特征清单必须包含58个不重复特征")
    return names


def read_csv(path: Path, table_name: str) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"{table_name}不存在: {path}")
    if path.suffix.lower() != ".csv":
        raise ValueError(f"{table_name}必须是 CSV 文件: {path}")
    frame = pd.read_csv(path, encoding="utf-8-sig")
    if frame.empty:
        raise ValueError(f"{table_name}不包含任何数据行: {path}")
    return frame


def require_columns(frame: pd.DataFrame, columns: dict[str, str], table_name: str) -> None:
    missing = [column for column in columns.values() if column not in frame.columns]
    if missing:
        raise ValueError(f"{table_name}缺少必要字段: {missing}")


def clean_text(value: Any) -> str | None:
    if pd.isna(value):
        return None
    text = str(value).strip()
    return text or None


def normalize_gender(value: Any) -> str | None:
    text = clean_text(value)
    if text is None:
        return None
    normalized = text.lower()
    if normalized in {"男", "male", "m", "1"}:
        return "male"
    if normalized in {"女", "female", "f", "0"}:
        return "female"
    raise ValueError(f"无法识别性别编码: {text!r}")


def parse_boolean(value: Any) -> int | None:
    if pd.isna(value):
        return None
    if isinstance(value, (bool, np.bool_)):
        return int(value)
    text = str(value).strip().lower()
    if text in {"true", "1", "yes", "y", "是", "有", "阳性", "+", "±"}:
        return 1
    if text in {"false", "0", "no", "n", "否", "无", "阴性", "-"}:
        return 0
    return None


def parse_symptom_result(value: Any) -> int:
    if clean_text(value) is None:
        return 0
    parsed = parse_boolean(value)
    if parsed is None:
        raise ValueError(f"无法识别症状结果: {value!r}")
    return parsed


def clean_patient_ids(frame: pd.DataFrame, column: str, table_name: str) -> pd.Series:
    patient_ids = frame[column].map(clean_text)
    if patient_ids.isna().any():
        raise ValueError(f"{table_name}存在缺失或空白患者ID")
    return patient_ids


def unique_patient_values(
    frame: pd.DataFrame,
    value_column: str,
    normalizer: Any,
) -> dict[str, list[Any]]:
    values: dict[str, list[Any]] = {}
    for patient_id, group in frame.groupby("_patient_id", sort=False):
        normalized = {normalizer(value) for value in group[value_column]}
        values[patient_id] = sorted(
            [
                value
                for value in normalized
                if value is not None and not pd.isna(value)
            ],
            key=str,
        )
    return values


def select_latest_lab_records(lab: pd.DataFrame) -> pd.DataFrame:
    selected = lab[lab[LAB_COLUMNS["name"]].map(clean_text).isin(LAB_NAME_MAP)].copy()
    selected[LAB_COLUMNS["name"]] = selected[LAB_COLUMNS["name"]].map(clean_text)
    selected = selected.dropna(subset=["_patient_id", LAB_COLUMNS["name"]])
    selected["_row_order"] = np.arange(len(selected))
    result_columns = [
        LAB_COLUMNS["standard_result"],
        LAB_COLUMNS["standard_result_norm"],
        LAB_COLUMNS["standard_normalized_quantitative"],
        LAB_COLUMNS["abnormal"],
    ]
    has_result = pd.Series(False, index=selected.index)
    for column in result_columns:
        has_result |= selected[column].notna() & selected[column].astype(str).str.strip().ne("")
    selected = selected.loc[has_result].copy()
    selected["_sort_time"] = pd.to_datetime(
        selected[LAB_COLUMNS["report_time"]], errors="coerce"
    ).fillna(pd.to_datetime(selected[LAB_COLUMNS["result_time"]], errors="coerce"))
    return (
        selected.sort_values(
            ["_patient_id", LAB_COLUMNS["name"], "_sort_time", "_row_order"],
            na_position="first",
        )
        .drop_duplicates(["_patient_id", LAB_COLUMNS["name"]], keep="last")
        .reset_index(drop=True)
    )


def resolve_demographics(
    symptom: pd.DataFrame,
    lab: pd.DataFrame,
    patient_ids: pd.Index,
) -> pd.DataFrame:
    lab_snapshot = lab.copy()
    lab_snapshot["_row_order"] = np.arange(len(lab_snapshot))
    lab_snapshot["_sort_time"] = pd.to_datetime(
        lab_snapshot[LAB_COLUMNS["report_time"]], errors="coerce"
    ).fillna(pd.to_datetime(lab_snapshot[LAB_COLUMNS["result_time"]], errors="coerce"))
    lab_snapshot = (
        lab_snapshot.sort_values(["_patient_id", "_sort_time", "_row_order"], na_position="first")
        .drop_duplicates("_patient_id", keep="last")
    )

    symptom_gender = unique_patient_values(
        symptom, SYMPTOM_COLUMNS["gender"], normalize_gender
    )
    lab_gender = unique_patient_values(lab_snapshot, LAB_COLUMNS["gender"], normalize_gender)
    symptom_age = unique_patient_values(
        symptom,
        SYMPTOM_COLUMNS["age"],
        lambda value: pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0],
    )
    lab_age = unique_patient_values(
        lab_snapshot,
        LAB_COLUMNS["age"],
        lambda value: pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0],
    )

    rows: list[dict[str, Any]] = []
    missing: list[str] = []
    for patient_id in patient_ids:
        symptom_genders = symptom_gender.get(patient_id, [])
        lab_genders = lab_gender.get(patient_id, [])
        if len(symptom_genders) > 1 or len(lab_genders) > 1:
            raise ValueError(f"患者 {patient_id} 的性别记录互相冲突")
        if symptom_genders and lab_genders and symptom_genders[0] != lab_genders[0]:
            raise ValueError(f"患者 {patient_id} 的症状表和检验表性别不一致")
        gender = (symptom_genders or lab_genders or [None])[0]
        ages = symptom_age.get(patient_id, []) or lab_age.get(patient_id, [])
        age = ages[0] if ages else None
        if gender is None or pd.isna(age):
            missing.append(patient_id)
        rows.append(
            {
                "patient_id": patient_id,
                "age": float(age) if age is not None and not pd.isna(age) else np.nan,
                "gender_male": int(gender == "male") if gender is not None else np.nan,
            }
        )
    if missing:
        raise ValueError(f"患者缺少年龄或性别: {missing[:8]}")
    return pd.DataFrame(rows).set_index("patient_id").reindex(patient_ids)


def build_symptom_features(
    symptom: pd.DataFrame, patient_ids: pd.Index
) -> pd.DataFrame:
    symptom_data = symptom.copy()
    symptom_data["_symptom_name"] = symptom_data[SYMPTOM_COLUMNS["name"]].map(clean_text)
    if symptom_data["_symptom_name"].isna().any():
        raise ValueError("症状表存在空白症状名称")
    unknown = sorted(set(symptom_data["_symptom_name"]) - set(SYMPTOM_NAME_MAP))
    if unknown:
        raise ValueError(f"发现未登记的症状名称: {unknown}")
    symptom_data["_positive"] = symptom_data[SYMPTOM_COLUMNS["result"]].map(
        parse_symptom_result
    )
    pivot = symptom_data.pivot_table(
        index="_patient_id",
        columns="_symptom_name",
        values="_positive",
        aggfunc="max",
        fill_value=0,
    ).reindex(patient_ids, fill_value=0)

    output = pd.DataFrame(index=patient_ids)
    for original_name, english_name in SYMPTOM_NAME_MAP.items():
        output[f"symptom_{english_name}"] = (
            pivot[original_name] if original_name in pivot.columns else 0
        )
    for system_name, members in SYMPTOM_SYSTEMS.items():
        member_features = [f"symptom_{SYMPTOM_NAME_MAP[name]}" for name in members]
        output[f"symptom_system_{system_name}"] = output[member_features].max(axis=1).astype(int)
    return output.astype(int)


def encode_qualitative_result(row: pd.Series) -> float:
    normalized = clean_text(row[LAB_COLUMNS["standard_result_norm"]])
    if normalized is not None:
        lowered = normalized.lower()
        if lowered in {"阳性", "positive", "+", "±"}:
            return 1.0
        if lowered in {"阴性", "negative", "-"}:
            return 0.0
    parsed = parse_boolean(row[LAB_COLUMNS["abnormal"]])
    return float(parsed) if parsed is not None else np.nan


def build_lab_features(
    selected: pd.DataFrame, patient_ids: pd.Index, feature_names: list[str]
) -> pd.DataFrame:
    output = pd.DataFrame(index=patient_ids)
    for original_name, english_name in sorted(LAB_NAME_MAP.items(), key=lambda item: item[1]):
        item = selected[selected[LAB_COLUMNS["name"]].eq(original_name)].set_index("_patient_id")
        measured_feature = f"lab_measured_{english_name}"
        output[measured_feature] = (
            pd.Series(1, index=item.index).reindex(patient_ids).fillna(0).astype(int)
        )

        if item.empty:
            result_types: set[str] = set()
        else:
            item = item.copy()
            item["_result_type"] = item[LAB_COLUMNS["result_type"]].map(
                lambda value: (clean_text(value) or "").upper()
            )
            result_types = set(item["_result_type"])
            unknown_types = sorted(result_types - {"QUANTIFY", "QUALITATIVE"})
            if unknown_types:
                raise ValueError(
                    f"检验项目 {original_name!r} 存在无法识别的类型: {unknown_types}"
                )

        quantitative = item[item["_result_type"].eq("QUANTIFY")] if result_types else item
        value_feature = f"lab_value_{english_name}"
        standard_norm = pd.to_numeric(
            quantitative[LAB_COLUMNS["standard_result_norm"]], errors="coerce"
        )
        standard_result = pd.to_numeric(
            quantitative[LAB_COLUMNS["standard_result"]], errors="coerce"
        )
        output[value_feature] = standard_norm.combine_first(standard_result).reindex(patient_ids)

        normalized_feature = f"lab_normalized_{english_name}"
        if normalized_feature in feature_names:
            output[normalized_feature] = pd.to_numeric(
                quantitative[LAB_COLUMNS["standard_normalized_quantitative"]],
                errors="coerce",
            ).reindex(patient_ids)

        positive_feature = f"lab_positive_{english_name}"
        if positive_feature in feature_names:
            qualitative = item[item["_result_type"].eq("QUALITATIVE")] if result_types else item
            output[positive_feature] = qualitative.apply(
                encode_qualitative_result, axis=1
            ).reindex(patient_ids)
    return output


def run_preprocessing(
    symptom_input: Path, lab_input: Path, output: Path, feature_list: Path
) -> pd.DataFrame:
    feature_names = load_feature_names(feature_list)
    symptom = read_csv(symptom_input, "症状输入")
    lab = read_csv(lab_input, "检验输入")
    require_columns(symptom, SYMPTOM_COLUMNS, "症状输入")
    require_columns(lab, LAB_COLUMNS, "检验输入")
    symptom = symptom.copy()
    lab = lab.copy()
    symptom["_patient_id"] = clean_patient_ids(
        symptom, SYMPTOM_COLUMNS["patient_id"], "症状输入"
    )
    lab["_patient_id"] = clean_patient_ids(lab, LAB_COLUMNS["patient_id"], "检验输入")
    patient_ids = pd.Index(
        sorted(set(symptom["_patient_id"]) | set(lab["_patient_id"])),
        name="patient_id",
    )
    metadata = resolve_demographics(symptom, lab, patient_ids)
    selected_labs = select_latest_lab_records(lab)
    features = pd.concat(
        [metadata, build_symptom_features(symptom, patient_ids), build_lab_features(selected_labs, patient_ids, feature_names)],
        axis=1,
    )
    features.index.name = "patient_id"
    features = features.reset_index()
    expected_columns = ["patient_id", *feature_names]
    missing = [column for column in expected_columns if column not in features.columns]
    if missing:
        raise ValueError(f"预处理未生成模型所需特征: {missing}")
    features = features[expected_columns]
    output.parent.mkdir(parents=True, exist_ok=True)
    features.to_csv(output, index=False, encoding="utf-8-sig")
    print(
        f"已写入: {output}（{len(features)} 位患者，{len(feature_names)} 个特征）",
        file=sys.stderr,
    )
    return features


def main() -> int:
    args = parse_args()
    try:
        run_preprocessing(
            symptom_input=args.symptom_input,
            lab_input=args.lab_input,
            output=args.output,
            feature_list=args.feature_list,
        )
    except (FileNotFoundError, OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
