from ingestion import ingest_data
from cleaning import clean_data
from validation import validate_data
from transformation import transform_data

def run_pipeline():
    print("=" * 50)
    print("HOSPITAL READMISSION ETL PIPELINE")
    print("=" * 50)

    print("\n1. INGESTION")
    df, mapping_df = ingest_data()

    print("\n2. CLEANING")
    df = clean_data(df)

    print("\n3. VALIDATION")
    df = validate_data(df)

    print("\n4. TRANSFORMATION")
    transform_data(df)

    print("\n" + "=" * 50)
    print("PIPELINE COMPLETED SUCCESSFULLY")
    print("=" * 50)

if __name__ == "__main__":
    run_pipeline()
