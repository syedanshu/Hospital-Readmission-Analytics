import pandas as pd

from src.monitor_data import FEATURES, build_report


def test_identical_baseline_has_no_drift_or_quality_alerts():
    baseline = pd.DataFrame({
        feature: ["A", "B", "A", "B"] for feature in FEATURES
    })
    for feature in FEATURES:
        if feature.endswith("_id") or feature in {
            "length_of_stay", "prior_admissions", "diagnosis_count", "medication_count"
        }:
            baseline[feature] = [1, 2, 1, 2]

    report = build_report(baseline, baseline.copy())

    assert all(not result["drift_alert"] for result in report["features"].values())
    assert all(not result["quality_alert"] for result in report["features"].values())
    assert all(result["psi"] == 0 for result in report["features"].values())
