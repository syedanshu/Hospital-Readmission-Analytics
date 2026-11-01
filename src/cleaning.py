import numpy as np
import pandas as pd

def clean_data(df):
    # Dataset uses '?' as a special missing-value code.
    df = df.replace("?", np.nan)

    df.columns = (
        df.columns.str.lower()
        .str.strip()
        .str.replace(" ", "_", regex=False)
    )

    text_columns = df.select_dtypes(include=["object"]).columns
    for column in text_columns:
        df[column] = df[column].astype("string").str.strip()

    df["gender"] = df["gender"].replace({
        "Unknown/Invalid": "Unknown"
    })

    df["readmitted"] = df["readmitted"].replace({
        "<30": "Readmitted <30 days",
        ">30": "Readmitted >30 days",
        "NO": "Not Readmitted"
    })

    numeric_columns = [
        "encounter_id", "patient_nbr", "admission_type_id",
        "discharge_disposition_id", "admission_source_id",
        "time_in_hospital", "num_lab_procedures", "num_procedures",
        "num_medications", "number_outpatient", "number_emergency",
        "number_inpatient", "number_diagnoses"
    ]

    for column in numeric_columns:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    return df
