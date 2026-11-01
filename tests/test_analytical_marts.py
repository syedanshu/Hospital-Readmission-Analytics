import pandas as pd

import src.transformation as transformation


def test_transform_writes_encounter_admission_diagnosis_and_patient_marts(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(transformation, "CLEANED_DIR", tmp_path / "cleaned")
    monkeypatch.setattr(transformation, "ANALYTICAL_DIR", tmp_path / "analytical")
    frame = pd.DataFrame({
        "encounter_id": [101, 102],
        "patient_nbr": [9001, 9001],
        "time_in_hospital": [3, 4],
        "number_inpatient": [0, 1],
        "number_outpatient": [1, 0],
        "number_emergency": [0, 0],
        "number_diagnoses": [2, 3],
        "num_medications": [5, 7],
        "readmitted": ["Not Readmitted", "Readmitted <30 days"],
        "race": ["Caucasian", "Caucasian"],
        "gender": ["Female", "Female"],
        "age": ["[50-60)", "[50-60)"],
        "admission_type_id": [1, 2],
        "discharge_disposition_id": [1, 1],
        "admission_source_id": [7, 1],
        "diag_1": ["250.83", "414.01"],
        "diag_2": ["276", None],
        "diag_3": [None, "401"],
    })

    transformation.transform_data(frame)

    analytical = pd.read_csv(tmp_path / "analytical" / "readmission_analytics.csv")
    admissions = pd.read_csv(tmp_path / "analytical" / "admissions.csv")
    diagnoses = pd.read_csv(tmp_path / "analytical" / "diagnoses.csv")
    patients = pd.read_csv(tmp_path / "analytical" / "patient_summary.csv")
    assert len(analytical) == len(admissions) == 2
    assert len(diagnoses) == 4
    assert patients.loc[0, "total_encounters"] == 2
    assert patients.loc[0, "total_readmissions"] == 1
