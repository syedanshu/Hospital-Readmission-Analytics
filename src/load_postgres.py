import os
import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

try:
    from src.db_utils import get_database_url
except ModuleNotFoundError:  # pragma: no cover - direct script execution fallback
    from db_utils import get_database_url

load_dotenv()


def get_engine():
    connection_string = get_database_url()
    return create_engine(connection_string)


def load_data():
    engine = get_engine()

    analytical_dir = ROOT_DIR / "data" / "analytical"
    analytics_df = pd.read_csv(analytical_dir / "readmission_analytics.csv")
    patient_df = pd.read_csv(analytical_dir / "patient_summary.csv")
    admission_df = pd.read_csv(analytical_dir / "admissions.csv")
    diagnosis_df = pd.read_csv(analytical_dir / "diagnoses.csv")

    is_postgres = engine.url.get_backend_name() == "postgresql"
    schema = "hospital" if is_postgres else None
    tables = {
        "readmission_analytics": analytics_df,
        "patient_summary": patient_df,
        "admissions": admission_df,
        "diagnoses": diagnosis_df,
    }

    with engine.begin() as connection:
        if is_postgres:
            connection.execute(text("CREATE SCHEMA IF NOT EXISTS hospital"))

        for table_name, frame in tables.items():
            exists = inspect(connection).has_table(table_name, schema=schema)
            if exists:
                table_ref = (
                    f'"{schema}"."{table_name}"'
                    if schema else f'"{table_name}"'
                )
                connection.execute(text(f"DELETE FROM {table_ref}"))
            frame.to_sql(
                table_name,
                connection,
                schema=schema,
                if_exists="append" if exists else "fail",
                index=False,
            )

    backend = "PostgreSQL" if is_postgres else "SQLite"
    print(f"Data successfully loaded into {backend}.")

if __name__ == "__main__":
    load_data()
