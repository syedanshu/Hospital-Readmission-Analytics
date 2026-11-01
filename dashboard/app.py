import os
import sys
from pathlib import Path

import joblib
import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv
from sqlalchemy import create_engine

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

try:
    from src.db_utils import get_database_url
except ModuleNotFoundError:  # pragma: no cover - local script execution fallback
    from db_utils import get_database_url

load_dotenv()

st.set_page_config(
    page_title="Hospital Readmission Analytics",
    layout="wide"
)

@st.cache_data
def load_data():
    connection_string = get_database_url()
    engine = create_engine(connection_string)

    if connection_string.startswith("sqlite"):
        return pd.read_sql_query(
            "SELECT * FROM readmission_analytics",
            engine
        )

    return pd.read_sql(
        "SELECT * FROM hospital.readmission_analytics",
        engine
    )

st.title("🏥 Hospital Readmission Analytics Dashboard")
st.write("Analysis of hospital admission and readmission patterns")

try:
    df = load_data()

    total_encounters = len(df)
    total_readmissions = df["readmission_flag"].sum()
    readmission_rate = total_readmissions / total_encounters * 100
    average_los = df["length_of_stay"].mean()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Encounters", f"{total_encounters:,}")
    col2.metric("Readmissions", f"{total_readmissions:,}")
    col3.metric("Readmission Rate", f"{readmission_rate:.2f}%")
    col4.metric("Average Length of Stay", f"{average_los:.2f} days")

    st.divider()

    st.subheader("1. Readmission Rate by Age Group")
    age_analysis = (
        df.groupby("age")
        .agg(encounters=("encounter_id", "count"),
             readmissions=("readmission_flag", "sum"))
        .reset_index()
    )
    age_analysis["readmission_rate"] = (
        age_analysis["readmissions"] / age_analysis["encounters"] * 100
    )
    st.plotly_chart(
        px.bar(age_analysis, x="age", y="readmission_rate",
               title="Readmission Rate by Age Group"),
        use_container_width=True
    )

    st.subheader("2. Readmission Distribution")
    counts = df["readmitted"].value_counts().reset_index()
    counts.columns = ["status", "count"]
    st.plotly_chart(
        px.pie(counts, names="status", values="count",
               title="Readmission Distribution"),
        use_container_width=True
    )

    st.subheader("3. Length of Stay Analysis")
    st.plotly_chart(
        px.histogram(df, x="length_of_stay", nbins=14,
                     title="Distribution of Length of Stay"),
        use_container_width=True
    )

    st.subheader("4. Diagnosis Count vs Readmission")
    diagnosis = (
        df.groupby("diagnosis_count")
        .agg(encounters=("encounter_id", "count"),
             readmissions=("readmission_flag", "sum"))
        .reset_index()
    )
    diagnosis["readmission_rate"] = (
        diagnosis["readmissions"] / diagnosis["encounters"] * 100
    )
    st.plotly_chart(
        px.line(diagnosis, x="diagnosis_count", y="readmission_rate",
                markers=True,
                title="Readmission Rate by Number of Diagnoses"),
        use_container_width=True
    )

    st.subheader("5. Medication Count vs Readmission")
    medication = (
        df.groupby("medication_count")
        .agg(encounters=("encounter_id", "count"),
             readmissions=("readmission_flag", "sum"))
        .reset_index()
    )
    medication["readmission_rate"] = (
        medication["readmissions"] / medication["encounters"] * 100
    )
    st.plotly_chart(
        px.scatter(medication, x="medication_count",
                   y="readmission_rate", size="encounters",
                   title="Medication Count vs Readmission Rate"),
        use_container_width=True
    )

    st.subheader("6. Readmission Rate by Primary Diagnosis")
    diagnosis = (
        df.groupby("diag_1", dropna=False)
        .agg(encounters=("encounter_id", "count"),
             readmissions=("readmission_flag", "sum"))
        .reset_index()
    )
    diagnosis = diagnosis[diagnosis["encounters"] >= 25].copy()
    diagnosis["readmission_rate"] = (
        diagnosis["readmissions"] / diagnosis["encounters"] * 100
    )
    st.plotly_chart(
        px.bar(
            diagnosis.nlargest(15, "readmission_rate"),
            x="diag_1", y="readmission_rate",
            title="Readmission Rate by Primary Diagnosis Code"
        ),
        use_container_width=True
    )

    st.subheader("7. Admissions by Admission Type")
    admission_type = (
        df.groupby("admission_type_id")
        .agg(encounters=("encounter_id", "count"),
             readmissions=("readmission_flag", "sum"))
        .reset_index()
    )
    admission_type["readmission_rate"] = (
        admission_type["readmissions"] / admission_type["encounters"] * 100
    )
    st.plotly_chart(
        px.bar(
            admission_type, x="admission_type_id", y="readmission_rate",
            hover_data=["encounters"],
            title="Readmission Rate by Admission Type Code"
        ),
        use_container_width=True
    )

    model_path = ROOT_DIR / "models" / "readmission_model.joblib"
    if model_path.exists():
        st.divider()
        st.subheader("Readmission Risk Prototype")
        st.warning(
            "Academic decision-support prototype only. Not for clinical use. "
            "Do not enter identifiable patient information."
        )
        with st.form("readmission_risk_form"):
            input_col1, input_col2, input_col3 = st.columns(3)
            with input_col1:
                selected_race = st.selectbox(
                    "Race group", sorted(df["race"].dropna().unique())
                )
                selected_gender = st.selectbox(
                    "Gender", sorted(df["gender"].dropna().unique())
                )
                selected_age = st.selectbox(
                    "Age group", sorted(df["age"].dropna().unique())
                )
                admission_type_id = st.number_input(
                    "Admission type code", min_value=1, max_value=8, value=1
                )
            with input_col2:
                discharge_disposition_id = st.number_input(
                    "Discharge code", min_value=1, max_value=30, value=1
                )
                admission_source_id = st.number_input(
                    "Admission source code", min_value=1, max_value=26, value=7
                )
                length_of_stay = st.number_input(
                    "Length of stay (days)", min_value=1, max_value=365, value=3
                )
            with input_col3:
                prior_admissions = st.number_input(
                    "Prior admissions", min_value=0, value=0
                )
                diagnosis_count = st.number_input(
                    "Diagnosis count", min_value=0, max_value=16, value=5
                )
                medication_count = st.number_input(
                    "Medication count", min_value=0, max_value=100, value=12
                )
            submitted = st.form_submit_button("Estimate risk")

        if submitted:
            features = pd.DataFrame([{
                "race": selected_race,
                "gender": selected_gender,
                "age": selected_age,
                "admission_type_id": admission_type_id,
                "discharge_disposition_id": discharge_disposition_id,
                "admission_source_id": admission_source_id,
                "length_of_stay": length_of_stay,
                "prior_admissions": prior_admissions,
                "diagnosis_count": diagnosis_count,
                "medication_count": medication_count,
            }])
            model = joblib.load(model_path)
            risk = float(model.predict_proba(features)[0, 1])
            st.metric("Estimated readmission probability", f"{risk:.1%}")

except Exception as e:
    st.error("Dashboard could not connect to PostgreSQL.")
    st.info("Run the ETL and PostgreSQL loading steps first.")
    st.exception(e)
