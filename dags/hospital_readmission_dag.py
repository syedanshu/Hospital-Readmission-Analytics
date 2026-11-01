"""
Airflow orchestration for the Hospital Readmission Part 1 ETL.

Set PROJECT_DIR to the absolute path of this project on your machine.
"""

import os
import sys
from datetime import datetime

from airflow import DAG
from airflow.operators.python import PythonOperator

PROJECT_DIR = os.environ.get(
    "HOSPITAL_PROJECT_DIR",
    os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
)

SRC_DIR = os.path.join(PROJECT_DIR, "src")
sys.path.insert(0, SRC_DIR)

from ingestion import ingest_data
from cleaning import clean_data
from validation import validate_data
from transformation import transform_data
from load_postgres import load_data


def clean_task():
    import pandas as pd
    staging_dir = os.path.join(PROJECT_DIR, "data", "staging")
    df = pd.read_csv(os.path.join(staging_dir, "diabetic_staging.csv"))
    df = clean_data(df)
    df.to_csv(os.path.join(staging_dir, "cleaned_staging.csv"), index=False)


def ingestion_task():
    df, mapping_df = ingest_data()
    return {
        "encounter_rows": len(df),
        "mapping_rows": len(mapping_df),
    }


def validation_task():
    import pandas as pd
    staging_dir = os.path.join(PROJECT_DIR, "data", "staging")
    df = pd.read_csv(os.path.join(staging_dir, "cleaned_staging.csv"))
    valid_df = validate_data(df)
    valid_path = os.path.join(staging_dir, "validated_staging.csv")
    valid_df.to_csv(valid_path, index=False)
    return len(valid_df)


def transformation_task():
    import pandas as pd
    staging_dir = os.path.join(PROJECT_DIR, "data", "staging")
    df = pd.read_csv(os.path.join(staging_dir, "validated_staging.csv"))
    transform_data(df)


with DAG(
    dag_id="hospital_readmission_etl",
    start_date=datetime(2026, 9, 1),
    schedule="@daily",
    catchup=False,
    max_active_runs=1,
    tags=["hospital", "etl", "mlops"],
) as dag:

    ingestion = PythonOperator(
        task_id="ingest_data",
        python_callable=ingestion_task
    )

    cleaning = PythonOperator(
        task_id="clean_data",
        python_callable=clean_task
    )

    validation = PythonOperator(
        task_id="validate_data",
        python_callable=validation_task
    )

    transformation = PythonOperator(
        task_id="transform_data",
        python_callable=transformation_task
    )

    postgres = PythonOperator(
        task_id="load_postgresql",
        python_callable=load_data
    )

    ingestion >> cleaning >> validation >> transformation >> postgres
