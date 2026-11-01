import os
from pathlib import Path
from datetime import datetime
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT_DIR / "data" / "raw"
STAGING_DIR = ROOT_DIR / "data" / "staging"
LOG_DIR = ROOT_DIR / "logs"


def _append_log(path, record):
    log_exists = path.exists()
    pd.DataFrame([record]).to_csv(
        path, mode="a", header=not log_exists, index=False
    )

def ingest_data():
    os.makedirs(STAGING_DIR, exist_ok=True)
    os.makedirs(LOG_DIR, exist_ok=True)

    source_file = RAW_DIR / "diabetic_data.csv"
    mapping_file = RAW_DIR / "IDS_mapping.csv"

    try:
        df = pd.read_csv(source_file)
        mapping_df = pd.read_csv(mapping_file)

        extracted_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_path = LOG_DIR / "ingestion_log.csv"
        for file_name, row_count in [
            (source_file.name, len(df)), (mapping_file.name, len(mapping_df))
        ]:
            _append_log(log_path, {
                "extraction_date": extracted_at,
                "source": "UCI Diabetes 130-US Hospitals Dataset",
                "file": file_name,
                "status": "SUCCESS",
                "row_count": row_count,
            })

        df.to_csv(STAGING_DIR / "diabetic_staging.csv", index=False)
        mapping_df.to_csv(STAGING_DIR / "IDS_mapping_staging.csv", index=False)

        print("Data ingestion successful.")
        print(f"Rows ingested: {len(df)}")
        return df, mapping_df

    except Exception as e:
        error = {
            "extraction_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "source": "UCI Diabetes 130-US Hospitals Dataset",
            "file": "diabetic_data.csv",
            "status": "FAILED",
            "error": str(e)
        }
        _append_log(LOG_DIR / "ingestion_error.csv", error)
        raise
