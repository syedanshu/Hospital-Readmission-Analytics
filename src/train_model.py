"""Train and register readmission models for the academic prototype."""

import json
import os
from pathlib import Path

import joblib
import mlflow
import mlflow.sklearn
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    brier_score_loss,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from xgboost import XGBClassifier

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT_DIR / "data" / "analytical" / "readmission_analytics.csv"
MODEL_DIR = ROOT_DIR / "models"
TARGET = "readmission_flag"
GROUP = "patient_key"
CATEGORICAL = ["race", "gender", "age"]
NUMERIC = [
    "admission_type_id", "discharge_disposition_id", "admission_source_id",
    "length_of_stay", "prior_admissions", "diagnosis_count", "medication_count",
]
FEATURES = CATEGORICAL + NUMERIC


def _group_split(frame):
    groups = frame[GROUP].fillna(
        pd.Series(frame.index.astype(str), index=frame.index)
    )
    outer = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
    train_validation_idx, test_idx = next(
        outer.split(frame, frame[TARGET], groups)
    )
    train_validation = frame.iloc[train_validation_idx]
    test = frame.iloc[test_idx]
    inner_groups = train_validation[GROUP].fillna(
        pd.Series(train_validation.index.astype(str), index=train_validation.index)
    )
    inner = GroupShuffleSplit(n_splits=1, test_size=0.25, random_state=43)
    train_idx, validation_idx = next(
        inner.split(train_validation, train_validation[TARGET], inner_groups)
    )
    train = train_validation.iloc[train_idx]
    validation = train_validation.iloc[validation_idx]
    return train, validation, test


def _build_pipeline(estimator):
    numeric = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scale", StandardScaler()),
    ])
    categorical = Pipeline([
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("encode", OneHotEncoder(handle_unknown="ignore")),
    ])
    preprocess = ColumnTransformer([
        ("numeric", numeric, NUMERIC),
        ("categorical", categorical, CATEGORICAL),
    ])
    return Pipeline([("preprocess", preprocess), ("model", estimator)])


def _metrics(model, frame):
    features = frame[FEATURES]
    labels = frame[TARGET].astype(int)
    probabilities = model.predict_proba(features)[:, 1]
    predictions = probabilities >= 0.5
    result = {
        "precision": precision_score(labels, predictions, zero_division=0),
        "recall": recall_score(labels, predictions, zero_division=0),
        "f1": f1_score(labels, predictions, zero_division=0),
        "brier_score": brier_score_loss(labels, probabilities),
    }
    result["roc_auc"] = (
        roc_auc_score(labels, probabilities) if labels.nunique() > 1 else float("nan")
    )
    return result


def _feature_importance(model):
    fitted_preprocess = model.named_steps["preprocess"]
    estimator = model.named_steps["model"]
    names = fitted_preprocess.get_feature_names_out()
    if hasattr(estimator, "feature_importances_"):
        values = estimator.feature_importances_
    else:
        values = np.abs(estimator.coef_).ravel()
    return pd.DataFrame({"feature": names, "importance": values}).sort_values(
        "importance", ascending=False
    )


def train_and_register(data_path=DATA_PATH):
    frame = pd.read_csv(data_path)
    required = set(FEATURES + [TARGET, GROUP])
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"Analytical dataset is missing required columns: {missing}")
    frame = frame.dropna(subset=[TARGET]).copy()
    frame[TARGET] = frame[TARGET].astype(int)
    if frame[TARGET].nunique() != 2:
        raise ValueError("Training requires both readmission classes.")

    train, validation, test = _group_split(frame)
    tracking_uri = os.getenv("MLFLOW_TRACKING_URI", "sqlite:///mlflow.db")
    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment("hospital-readmission-risk")

    positive_count = int(train[TARGET].sum())
    negative_count = len(train) - positive_count
    candidates = {
        "logistic_regression": LogisticRegression(
            max_iter=1000, class_weight="balanced", random_state=42
        ),
        "random_forest": RandomForestClassifier(
            n_estimators=300, min_samples_leaf=4,
            class_weight="balanced_subsample", n_jobs=-1, random_state=42,
        ),
        "xgboost": XGBClassifier(
            n_estimators=300, max_depth=5, learning_rate=0.05,
            subsample=0.85, colsample_bytree=0.85,
            scale_pos_weight=negative_count / max(positive_count, 1),
            eval_metric="logloss", n_jobs=-1, random_state=42,
        ),
    }

    results = []
    for name, estimator in candidates.items():
        pipeline = _build_pipeline(estimator)
        with mlflow.start_run(run_name=name) as run:
            mlflow.log_params({
                "model": name,
                "split_strategy": "patient_grouped_60_20_20",
                "random_state": 42,
                "threshold": 0.5,
                "train_rows": len(train),
                "validation_rows": len(validation),
                "test_rows": len(test),
            })
            pipeline.fit(train[FEATURES], train[TARGET])
            validation_metrics = _metrics(pipeline, validation)
            mlflow.log_metrics({f"validation_{key}": value for key, value in validation_metrics.items()})
            results.append((name, pipeline, validation_metrics["f1"], run.info.run_id))

    winner_name, _, _, _ = max(results, key=lambda result: result[2])
    winning_estimator = candidates[winner_name]
    final_model = _build_pipeline(winning_estimator)
    training_rows = pd.concat([train, validation], ignore_index=True)
    final_model.fit(training_rows[FEATURES], training_rows[TARGET])
    test_metrics = _metrics(final_model, test)

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    model_path = MODEL_DIR / "readmission_model.joblib"
    temporary_model = MODEL_DIR / "readmission_model.joblib.tmp"
    joblib.dump(final_model, temporary_model)
    temporary_model.replace(model_path)
    importance_path = MODEL_DIR / "feature_importance.csv"
    _feature_importance(final_model).to_csv(importance_path, index=False)
    metadata = {
        "model_name": winner_name,
        "target": TARGET,
        "threshold": 0.5,
        "features": FEATURES,
        "group_key": GROUP,
        "split_strategy": "patient_grouped_60_20_20",
        "test_metrics": test_metrics,
        "intended_use": "Academic decision-support prototype; not for clinical use.",
    }
    metadata_path = MODEL_DIR / "model_metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    with mlflow.start_run(run_name=f"selected_{winner_name}"):
        mlflow.log_params({
            "selected_model": winner_name,
            "selection_metric": "validation_f1",
            "validation_f1": max(result[2] for result in results),
            "split_strategy": "patient_grouped_60_20_20",
        })
        mlflow.log_metrics({f"test_{key}": value for key, value in test_metrics.items()})
        mlflow.log_artifact(str(importance_path))
        mlflow.log_artifact(str(metadata_path))
        mlflow.sklearn.log_model(
            final_model,
            artifact_path="model",
            registered_model_name="hospital-readmission-risk",
            serialization_format="cloudpickle",
        )

    print(f"Selected model: {winner_name}")
    print(f"Held-out test metrics: {test_metrics}")
    print(f"Model artifact: {model_path}")
    return metadata


if __name__ == "__main__":
    train_and_register()
