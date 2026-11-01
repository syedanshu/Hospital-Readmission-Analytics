CREATE SCHEMA IF NOT EXISTS hospital;

CREATE TABLE IF NOT EXISTS hospital.readmission_analytics (
    encounter_id BIGINT PRIMARY KEY,
    patient_key VARCHAR(16),
    race VARCHAR(50),
    gender VARCHAR(20),
    age VARCHAR(20),
    admission_type_id INTEGER,
    discharge_disposition_id INTEGER,
    admission_source_id INTEGER,
    length_of_stay INTEGER,
    prior_admissions INTEGER,
    diagnosis_count INTEGER,
    medication_count INTEGER,
    readmitted VARCHAR(30),
    readmission_flag INTEGER,
    diag_1 VARCHAR(20)
);

CREATE TABLE IF NOT EXISTS hospital.patient_summary (
    patient_key VARCHAR(16) PRIMARY KEY,
    total_encounters INTEGER,
    total_readmissions INTEGER,
    average_length_of_stay NUMERIC,
    average_medications NUMERIC,
    average_diagnoses NUMERIC
);

CREATE TABLE IF NOT EXISTS hospital.admissions (
    encounter_id BIGINT PRIMARY KEY,
    patient_key VARCHAR(16),
    admission_type_id INTEGER,
    discharge_disposition_id INTEGER,
    admission_source_id INTEGER,
    length_of_stay INTEGER,
    prior_admissions INTEGER,
    readmitted VARCHAR(30),
    readmission_flag INTEGER
);

CREATE TABLE IF NOT EXISTS hospital.diagnoses (
    encounter_id BIGINT NOT NULL,
    diagnosis_rank VARCHAR(10) NOT NULL,
    diagnosis_code VARCHAR(20) NOT NULL,
    PRIMARY KEY (encounter_id, diagnosis_rank)
);
