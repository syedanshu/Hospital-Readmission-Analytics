import os
import pandas as pd

LOG_DIR = "logs"

def validate_data(df):
    os.makedirs(LOG_DIR, exist_ok=True)
    rejected_records = []

    invalid_encounter = df[df["encounter_id"].isna()]
    for _, row in invalid_encounter.iterrows():
        rejected_records.append({
            "encounter_id": row.get("encounter_id"),
            "reason": "Missing encounter_id"
        })

    duplicate_mask = df.duplicated(subset=["encounter_id"], keep=False)
    duplicates = df[duplicate_mask]
    for _, row in duplicates.iterrows():
        rejected_records.append({
            "encounter_id": row["encounter_id"],
            "reason": "Duplicate encounter_id"
        })

    invalid_los = df[
        (df["time_in_hospital"] < 1) |
        (df["time_in_hospital"] > 365)
    ]
    for _, row in invalid_los.iterrows():
        rejected_records.append({
            "encounter_id": row["encounter_id"],
            "reason": "Invalid length of stay"
        })

    rejected_df = pd.DataFrame(rejected_records)
    rejected_df.to_csv(
        os.path.join(LOG_DIR, "rejected_records.csv"), index=False
    )

    df = df[df["encounter_id"].notna()].copy()
    df = df.drop_duplicates(subset=["encounter_id"])
    df = df[
        (df["time_in_hospital"] >= 1) &
        (df["time_in_hospital"] <= 365)
    ].copy()

    print(f"Rejected records: {len(rejected_df)}")
    print(f"Valid records: {len(df)}")
    return df
