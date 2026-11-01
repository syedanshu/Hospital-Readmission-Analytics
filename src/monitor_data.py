"""Compare incoming feature data with the model's training reference."""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import brier_score_loss, f1_score, precision_score, recall_score

ROOT_DIR = Path(__file__).resolve().parent.parent
FEATURES = [
    "race", "gender", "age", "admission_type_id",
    "discharge_disposition_id", "admission_source_id", "length_of_stay",
    "prior_admissions", "diagnosis_count", "medication_count",
]
NUMERIC = {
    "admission_type_id", "discharge_disposition_id", "admission_source_id",
    "length_of_stay", "prior_admissions", "diagnosis_count", "medication_count",
}


def _psi(expected, actual, bins=10):
    expected = pd.Series(expected).dropna()
    actual = pd.Series(actual).dropna()
    if expected.empty or actual.empty:
        return float("nan")
    if expected.nunique() <= 10:
        categories = sorted(set(expected.astype(str)) | set(actual.astype(str)))
        expected_rates = expected.astype(str).value_counts(normalize=True).reindex(categories, fill_value=0)
        actual_rates = actual.astype(str).value_counts(normalize=True).reindex(categories, fill_value=0)
    else:
        edges = np.unique(np.quantile(expected, np.linspace(0, 1, bins + 1)))
        if len(edges) < 3:
            return 0.0
        edges[0], edges[-1] = -np.inf, np.inf
        expected_rates = pd.cut(expected, bins=edges, include_lowest=True).value_counts(normalize=True).sort_index()
        actual_rates = pd.cut(actual, bins=edges, include_lowest=True).value_counts(normalize=True).sort_index()
        actual_rates = actual_rates.reindex(expected_rates.index, fill_value=0)
    epsilon = 1e-6
    expected_rates = expected_rates.clip(lower=epsilon)
    actual_rates = actual_rates.clip(lower=epsilon)
    return float(((actual_rates - expected_rates) * np.log(actual_rates / expected_rates)).sum())


def build_report(baseline, current, model_path=None):
    missing_columns = sorted(set(FEATURES) - set(baseline.columns) | (set(FEATURES) - set(current.columns)))
    if missing_columns:
        raise ValueError(f"Missing required feature columns: {missing_columns}")
    report = {
        "baseline_rows": len(baseline),
        "current_rows": len(current),
        "features": {},
    }
    for feature in FEATURES:
        baseline_missing = float(baseline[feature].isna().mean())
        current_missing = float(current[feature].isna().mean())
        if feature in NUMERIC:
            expected = pd.to_numeric(baseline[feature], errors="coerce")
            observed = pd.to_numeric(current[feature], errors="coerce")
        else:
            expected, observed = baseline[feature], current[feature]
        psi = _psi(expected, observed)
        report["features"][feature] = {
            "baseline_missing_rate": baseline_missing,
            "current_missing_rate": current_missing,
            "psi": psi,
            "drift_alert": bool(np.isfinite(psi) and psi >= 0.2),
            "quality_alert": current_missing > max(0.05, baseline_missing + 0.05),
        }

    if model_path and "readmission_flag" in current.columns:
        import joblib

        model = joblib.load(model_path)
        probabilities = model.predict_proba(current[FEATURES])[:, 1]
        probability_series = pd.Series(probabilities, index=current.index)
        predictions = probabilities >= 0.5
        labels = current["readmission_flag"].astype(int)

        def classification_metrics(rows):
            row_probabilities = probability_series.loc[rows.index].to_numpy()
            row_predictions = row_probabilities >= 0.5
            row_labels = rows["readmission_flag"].astype(int)
            return {
                "rows": len(rows),
                "precision": float(precision_score(
                    row_labels, row_predictions, zero_division=0
                )),
                "recall": float(recall_score(
                    row_labels, row_predictions, zero_division=0
                )),
                "f1": float(f1_score(
                    row_labels, row_predictions, zero_division=0
                )),
                "brier_score": float(brier_score_loss(
                    row_labels, row_probabilities
                )),
            }

        report["performance"] = {
            "precision": float(precision_score(labels, predictions, zero_division=0)),
            "recall": float(recall_score(labels, predictions, zero_division=0)),
            "f1": float(f1_score(labels, predictions, zero_division=0)),
            "brier_score": float(brier_score_loss(labels, probabilities)),
        }
        report["subgroup_performance"] = {}
        for subgroup in ("race", "gender", "age"):
            report["subgroup_performance"][subgroup] = {
                str(value): classification_metrics(rows)
                for value, rows in current.groupby(subgroup, dropna=False)
                if len(rows) >= 30
            }
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", default=str(ROOT_DIR / "data/analytical/readmission_analytics.csv"))
    parser.add_argument("--current", required=True, help="CSV of recent scored or incoming records")
    parser.add_argument("--output", default=str(ROOT_DIR / "logs/drift_report.json"))
    parser.add_argument("--labeled", action="store_true", help="Evaluate performance when current data has labels")
    args = parser.parse_args()
    baseline = pd.read_csv(args.baseline)
    current = pd.read_csv(args.current)
    model_path = ROOT_DIR / "models" / "readmission_model.joblib" if args.labeled else None
    report = build_report(baseline, current, model_path)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, allow_nan=True), encoding="utf-8")
    print(f"Drift report written to {output}")


if __name__ == "__main__":
    main()
