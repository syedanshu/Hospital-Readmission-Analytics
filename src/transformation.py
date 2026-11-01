import hashlib
import os
from pathlib import Path
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parent.parent
CLEANED_DIR = ROOT_DIR / "data" / "cleaned"
ANALYTICAL_DIR = ROOT_DIR / "data" / "analytical"

def create_surrogate_key(patient_nbr):
    if pd.isna(patient_nbr):
        return None
    value = str(int(patient_nbr))
    return hashlib.sha256(value.encode()).hexdigest()[:16]

def transform_data(df):
    os.makedirs(CLEANED_DIR, exist_ok=True)
    os.makedirs(ANALYTICAL_DIR, exist_ok=True)

    df["patient_key"] = df["patient_nbr"].apply(create_surrogate_key)
    df["length_of_stay"] = df["time_in_hospital"]

    df["prior_admissions"] = (
        df["number_inpatient"].fillna(0)
        + df["number_outpatient"].fillna(0)
        + df["number_emergency"].fillna(0)
    )

    df["diagnosis_count"] = df["number_diagnoses"]
    df["medication_count"] = df["num_medications"]

    df["readmission_flag"] = (
        df["readmitted"] != "Not Readmitted"
    ).astype(int)

    df.to_csv(CLEANED_DIR / "hospital_readmission_cleaned.csv", index=False)

    columns = [
        "encounter_id", "patient_key", "race", "gender", "age",
        "admission_type_id", "discharge_disposition_id",
        "admission_source_id", "length_of_stay", "prior_admissions",
        "diagnosis_count", "medication_count", "readmitted",
        "readmission_flag", "diag_1"
    ]

    analytical_df = df[columns].copy()
    analytical_df.to_csv(ANALYTICAL_DIR / "readmission_analytics.csv", index=False)

    admission_columns = [
        "encounter_id", "patient_key", "admission_type_id",
        "discharge_disposition_id", "admission_source_id",
        "length_of_stay", "prior_admissions", "readmitted",
        "readmission_flag"
    ]
    df[admission_columns].to_csv(
        ANALYTICAL_DIR / "admissions.csv", index=False
    )

    diagnosis_columns = ["encounter_id", "diag_1", "diag_2", "diag_3"]
    diagnoses = df[diagnosis_columns].melt(
        id_vars="encounter_id",
        var_name="diagnosis_rank",
        value_name="diagnosis_code"
    )
    diagnoses = diagnoses[diagnoses["diagnosis_code"].notna()].copy()
    diagnoses.to_csv(ANALYTICAL_DIR / "diagnoses.csv", index=False)

    patient_summary = (
        df.groupby("patient_key")
        .agg(
            total_encounters=("encounter_id", "count"),
            total_readmissions=("readmission_flag", "sum"),
            average_length_of_stay=("length_of_stay", "mean"),
            average_medications=("medication_count", "mean"),
            average_diagnoses=("diagnosis_count", "mean")
        )
        .reset_index()
    )

    patient_summary.to_csv(ANALYTICAL_DIR / "patient_summary.csv", index=False)

    print("Transformation completed.")
    print(f"Analytical rows: {len(analytical_df)}")
    print(f"Patients: {len(patient_summary)}")

    return analytical_df, patient_summary
