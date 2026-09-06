"""Run the frozen CAP ExtraTrees model on a preprocessed feature CSV file."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd


HERE = Path(__file__).resolve().parent
DEFAULT_MODEL = HERE / "extra_trees_sqrt_logloss.joblib"
DEFAULT_FEATURE_LIST = HERE / "feature_list.json"
DEFAULT_INPUT = HERE / "preprocessed_features.csv"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="使用冻结的 ExtraTrees CAP 风险模型计算肺炎类得分。"
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help="预处理后的特征 CSV；必须包含 feature_list.json 中的 58 个特征。",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="输出 CSV；不指定时将结果写到标准输出。",
    )
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--feature-list", type=Path, default=DEFAULT_FEATURE_LIST)
    parser.add_argument(
        "--threshold",
        type=float,
        default=None,
        help="可选分类阈值（0 到 1）。指定后额外输出 predicted_label；不指定只输出模型得分。",
    )
    return parser.parse_args()


def load_feature_names(path: Path) -> list[str]:
    if not path.exists():
        raise FileNotFoundError(f"特征清单不存在: {path}")
    try:
        names = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"特征清单不是有效 JSON: {path}") from exc
    if not isinstance(names, list) or not all(isinstance(name, str) for name in names):
        raise ValueError("特征清单必须是字符串列表")
    if len(names) != 58:
        raise ValueError(f"特征清单必须包含 58 个特征，实际为 {len(names)}")
    if len(names) != len(set(names)):
        raise ValueError("特征清单存在重复列名")
    return names


def read_input(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"输入文件不存在: {path}")
    if path.suffix.lower() != ".csv":
        raise ValueError("当前推理入口只接受 CSV 输入文件")
    frame = pd.read_csv(path, encoding="utf-8-sig")
    if frame.empty:
        raise ValueError("输入 CSV 不包含任何数据行")
    return frame


def _bad_cells(mask: pd.DataFrame, frame: pd.DataFrame) -> list[str]:
    locations: list[str] = []
    for row_index, column_index in np.argwhere(mask.to_numpy()):
        column = str(mask.columns[column_index])
        value = frame.iloc[row_index, column_index]
        locations.append(f"第 {row_index + 2} 行 {column}={value!r}")
        if len(locations) == 8:
            break
    return locations


def prepare_features(frame: pd.DataFrame, feature_names: list[str]) -> tuple[pd.DataFrame, pd.Series]:
    missing = [name for name in feature_names if name not in frame.columns]
    if missing:
        raise ValueError(f"输入缺少特征列（共 {len(missing)} 个）: {missing}")

    if "patient_id" in frame.columns:
        patient_ids = frame["patient_id"].astype("string").str.strip()
        if patient_ids.isna().any() or patient_ids.eq("").any():
            raise ValueError("patient_id 不能为空")
        if patient_ids.duplicated().any():
            raise ValueError("patient_id 必须唯一")
    else:
        patient_ids = pd.Series(
            [f"row_{index}" for index in range(1, len(frame) + 1)],
            dtype="string",
            name="patient_id",
        )

    raw = frame[feature_names]
    numeric = raw.apply(pd.to_numeric, errors="coerce")
    invalid = raw.notna() & numeric.isna()
    if invalid.any().any():
        details = "; ".join(_bad_cells(invalid, raw))
        raise ValueError(f"特征必须是数值或空值；发现无法解析的值: {details}")

    non_finite = numeric.notna() & ~np.isfinite(numeric)
    if non_finite.any().any():
        details = "; ".join(_bad_cells(non_finite, raw))
        raise ValueError(f"特征不能包含无穷大: {details}")

    return numeric, patient_ids


def positive_scores(model: object, features: pd.DataFrame) -> np.ndarray:
    if not hasattr(model, "predict_proba"):
        raise TypeError("模型不支持 predict_proba，无法计算肺炎类得分")

    model_feature_names = getattr(model, "feature_names_in_", None)
    if model_feature_names is not None and list(model_feature_names) != list(features.columns):
        raise ValueError("输入特征顺序与模型保存时的特征顺序不一致")

    probabilities = np.asarray(model.predict_proba(features), dtype=float)
    classes = getattr(model, "classes_", None)
    if classes is None and hasattr(model, "named_steps"):
        estimator = model.named_steps.get("model")
        classes = getattr(estimator, "classes_", None)
    if classes is None:
        raise ValueError("无法从模型读取类别顺序")
    positive_indices = np.flatnonzero(np.asarray(classes) == 1)
    if len(positive_indices) != 1:
        raise ValueError(f"模型类别中必须恰好包含正类 1，实际为 {classes}")
    return probabilities[:, int(positive_indices[0])]


def run(args: argparse.Namespace) -> pd.DataFrame:
    if args.threshold is not None and not 0 <= args.threshold <= 1:
        raise ValueError("threshold 必须在 0 到 1 之间")

    feature_names = load_feature_names(args.feature_list)
    input_frame = read_input(args.input)
    features, patient_ids = prepare_features(input_frame, feature_names)
    model = joblib.load(args.model)
    scores = positive_scores(model, features)

    result = pd.DataFrame(
        {
            "patient_id": patient_ids.astype(str),
            "pneumonia_score": scores,
        }
    )
    if args.threshold is not None:
        result["threshold"] = float(args.threshold)
        result["predicted_label"] = (scores >= args.threshold).astype(int)
        result["predicted_class"] = np.where(
            scores >= args.threshold, "肺炎", "上感"
        )
    return result


def write_output(result: pd.DataFrame, output: Path | None) -> None:
    if output is None:
        result.to_csv(sys.stdout, index=False, float_format="%.12g")
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output, index=False, encoding="utf-8-sig", float_format="%.12g")
    print(f"已写入: {output}", file=sys.stderr)


def main() -> int:
    args = parse_args()
    try:
        result = run(args)
        write_output(result, args.output)
    except (FileNotFoundError, OSError, TypeError, ValueError) as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
