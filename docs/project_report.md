# Hospital Readmission Analytics and Risk Prototype

## 1. Executive Summary

This project implements a reproducible pipeline for the UCI Diabetes 130-US Hospitals dataset and extends it with an academic readmission-risk modeling workflow. The Part 1 system ingests the supplied de-identified encounter and mapping CSVs, retains source files in a local landing area, records ingestion status, cleans and validates encounters, creates encounter/admission/diagnosis/patient-summary data marts, and serves seven analytics views in Streamlit. PostgreSQL is the configured target; SQLite is supported as a local fallback when PostgreSQL is unavailable.

Part 2 compares Logistic Regression, Random Forest, and XGBoost. The split groups by patient key to reduce patient-level leakage. MLflow stores experiment parameters, validation and test metrics, model artifacts, and a registered selected model. A FastAPI endpoint serves aggregate-feature predictions, and a batch utility checks input quality, feature drift, and performance when labels arrive. This is an academic prototype, not a clinical device or recommendation system.

## 2. Problem and Scope

Hospital readmission is a useful operational outcome for studying utilization and care transitions. This project describes patterns in the source cohort and demonstrates the engineering lifecycle for a predictive model. It does not estimate a causal effect, make treatment recommendations, or claim that a high-risk score should change care.

The target is derived from the dataset-defined `readmitted` label: both `<30` and `>30` categories are positive, and `NO` is negative. Therefore it is not a pure 30-day readmission target. No encounter date is provided for a defensible chronological split. The dataset has admission type, admission source, and diagnosis codes, but no department identifier. Analysis uses the available fields and does not fabricate those missing dimensions.

## 3. Data Source and Privacy

The sole selected source is the UCI Diabetes 130-US Hospitals for Years 1999-2008 dataset. It contains de-identified encounters and a separate mapping file for source code descriptions. Acquisition is from the UCI Machine Learning Repository dataset page linked in the README. Students must download the original CSV files and place them in `data/raw/`; Kaggle and credentialed MIMIC-IV access are not needed.

The source's patient number is an identifier within the supplied data, not a direct identity. A deterministic truncated SHA-256 key is created for grouping and patient summaries. Hashing is pseudonymization, not a guarantee of anonymity; the key and encounter data remain protected and local. The model excludes both encounter IDs and patient keys, and the API logs request metadata without feature values. No personal information is added to the project.

## 4. Architecture and Data Flow

The architecture diagram is maintained in `docs/architecture.md`. The raw layer contains the original downloaded files. Python/Pandas reads those files, writes source copies to staging, and appends per-file extraction time, source, status, and row count to `logs/ingestion_log.csv`. Failures append to `logs/ingestion_error.csv`. Cleaning normalizes columns and missing-value codes. Validation emits rejected encounter IDs and reasons. Transformation derives utilization measures and writes analytical tables. The Airflow DAG sequences ingestion, cleaning, validation, transformation, and database loading.

The storage schema is in `database/schema.sql`. `hospital.readmission_analytics` supports aggregate analysis; `hospital.admissions`, `hospital.diagnoses`, and `hospital.patient_summary` expose related grains. The loader can use PostgreSQL or the SQLite development fallback. Streamlit reads the analytical table and presents cohort metrics plus seven comparisons. Part 2 reads that curated table, trains and selects a model, logs runs to MLflow, registers the selected version, and writes a local artifact used by FastAPI. Batch monitoring compares later data with the training reference.

## 5. ETL, Quality, and Data Mart

The pipeline changes `?` to null, standardizes column names and text whitespace, converts coded/numeric fields, and standardizes the readmission outcome. Encounters are rejected for missing IDs, duplicate IDs, or length of stay outside 1-365 days. Rejection reasons are written to CSV for review. The input CSVs are not manually transformed; each run regenerates staging, cleaned, and analytical outputs from raw files.

Derived fields include length of stay, prior utilization count (inpatient + outpatient + emergency), diagnosis count, medication count, binary readmission flag, and patient key. The encounter mart keeps one row per encounter; the diagnosis mart uses one row per encounter and diagnosis position; the patient summary aggregates encounters and utilization by patient key. Field definitions and rule details are in `docs/data_dictionary.md`.

## 6. Dashboard and Interpretation

The Streamlit dashboard provides total encounters, readmissions, readmission rate, and average length of stay, along with readmission rate by age group, readmission-class distribution, length-of-stay distribution, diagnosis-count comparison, medication-count comparison, primary diagnosis-code comparison, and admission-type comparison. After training, an optional form feeds non-identifying aggregate features into the local selected model and displays a probability. Low-frequency diagnosis groups are filtered for the displayed diagnosis comparison. These are descriptive rates; no causal interpretation is warranted, and code descriptions should be joined from validated lookup data before business-facing interpretation.

## 7. Model Development and Evaluation

The model target is the dataset-defined binary class. Candidate algorithms are Logistic Regression, Random Forest, and XGBoost. All use a shared preprocessing pipeline with numeric imputation/scaling and categorical imputation/one-hot encoding. Encounter ID, patient key, primary diagnosis, and outcome-derived fields are excluded from predictors. Current features include demographics, admission/discharge/source codes, length of stay, prior utilization, number of diagnoses, and medication count.

A reproducible patient-grouped 60/20/20 train/validation/test split is used: groups do not cross partitions. The validation F1 at a 0.5 threshold chooses a candidate; the selected pipeline is refit on training plus validation data and evaluated once on held-out test data. This patient grouping is preferable to a random encounter split for repeated encounters, but without timestamps it does not measure prospective temporal performance. Metrics include precision, recall, F1, ROC-AUC, and Brier score as a calibration measure. Threshold and model choice require further clinical and operational review before any use beyond coursework.

The executed patient-grouped run selected XGBoost by validation F1 and registered model version 1 in MLflow. On the held-out test partition it achieved precision 0.610, recall 0.624, F1 0.617, ROC-AUC 0.695, and Brier score 0.221. These values are a single split on this historical cohort, are not external validation, and must not be interpreted as clinical performance. `python -m src.train_model` regenerates the measured results, model artifact, top-feature importance file, metadata, MLflow run records, and registered model version. The MLflow run remains the experiment record of the parameters and artifacts.

## 8. Serving, Monitoring, and Lifecycle

FastAPI exposes `/health`, `/metrics`, and `/predict`. The prediction response is a probability plus a fixed demonstration threshold and an academic-use warning. Inputs are encounter-level aggregate features, schema-validated before scoring. Request timing and failure counts are collected without storing feature payloads. The service is local by default and must not be exposed publicly with real-world health data.

`src/monitor_data.py` compares current input distributions to the baseline using missingness and population stability index (PSI), with a PSI alert threshold of 0.2. When labeled current data is provided, it reports precision, recall, F1, and Brier score. A production system would additionally need persistent telemetry, subgroup fairness review, calibrated thresholds, alert routing, privacy/security controls, and approved retraining governance. Retraining should be considered only after validated labels accumulate and a documented quality, drift, or performance trigger is met; each retraining run must be evaluated against the existing holdout protocol and registered with its data/model lineage.

Docker packaging is provided for inference. Train and register the model before building the image so `models/readmission_model.joblib` exists. Containerization does not itself make the model production-ready.

## 9. Demonstration and Limitations

The project includes an Airflow DAG and task logs under `airflow_home/logs/` from previous executions. The assignment demonstration should show one fresh run from ingestion through database load and the Streamlit dashboard. Verify the target database backend before presenting: if PostgreSQL is not configured/reachable, the project deliberately falls back to local SQLite. Store screenshots of the successful run and dashboard in the submission package only after capturing them locally; this report does not claim screenshots that are not present.

Limitations include the historical 1999-2008 cohort, aggregated codes, missing department and event-time fields, a dataset-defined rather than guaranteed 30-day outcome, pseudonymous repeated-patient linkage, possible label and population shift, and lack of external validation. The model is for educational demonstration only and must not guide patient care.

## 10. Reproduction Checklist

1. Download the two UCI CSVs into `data/raw/` and verify the source files are unchanged.
2. Install dependencies and run `python src/pipeline.py`.
3. Initialize the database schema, then run `python src/load_postgres.py`.
4. Start the Airflow DAG and Streamlit dashboard; retain fresh execution evidence.
5. Train with `python -m src.train_model` and inspect metrics, feature importance, and the MLflow registry.
6. Start FastAPI locally and test `/health` and `/predict` with a synthetic example.
7. Run the batch drift command on an appropriate later input extract; review data quality and drift alerts before any retraining.

## 11. Cohort Profile and Descriptive Findings

The reproducible local ETL processed 101,766 encounters and produced patient summaries for 71,518 distinct surrogate keys. Under the current validation rules, zero rows were rejected in this run. This does not mean every source field is complete: race has missing values, and missingness is preserved rather than silently inventing a category. The supplied cohort covers years 1999-2008 and must not be treated as representative of current hospital populations.

The source outcome contains 54,864 encounters with no readmission, 35,545 with readmission after 30 days, and 11,357 with readmission within 30 days. The binary modeling target merges the latter two groups, resulting in a cohort readmission proportion of approximately 46.1%. This figure is specific to the encounter-level dataset and should not be compared directly with a hospital's patient-level 30-day readmission measure. Repeated encounters contribute multiple rows, which is why encounter and patient denominators must be clearly identified in any presentation.

Mean length of stay in the validated cohort is approximately 4.40 days and the median is 4 days. Descriptive binary-label rates vary by age band: the 70-80 and 80-90 groups are approximately 48.1% and 48.3%, while the 0-10 group is 18.0% based on only 161 encounters. These are unadjusted descriptive comparisons. Small group sizes, cohort selection, multiple encounters per person, and historical coding practices prevent causal or clinical conclusions. The dashboard presents the pattern for exploration, not as evidence that age causes readmission.

## 12. Pipeline Task Contracts and Evidence

The Python ingestion function reads the original encounter and ID-mapping files without rewriting them. It writes source-aligned copies into staging and appends one metadata row per source file to the ingestion log. The log records the extraction timestamp, dataset name, filename, success status, and number of rows. A failed read appends an error entry and re-raises the exception so an orchestrator will mark the task failed instead of continuing with partial inputs.

Cleaning is deterministic and does not use dashboard or model outputs. Validation writes a rejection file and returns only valid encounter rows. In Airflow, those validated rows are written to `validated_staging.csv`; the task returns a count to XCom rather than a full 100,000-row DataFrame. This keeps intermediate data on the project storage boundary and avoids bloating orchestration metadata. Transformation reads that persisted artifact, writes the cleaned encounter data and four analytical outputs, and the final task loads those outputs to the database. Root-relative paths are used for task artifacts so Airflow's process working directory does not change where outputs are written.

The database refresh runs in a transaction. Existing tables are emptied and appended to rather than dropped and recreated, so PostgreSQL primary keys and declared column types from `database/schema.sql` survive scheduled reruns. On the development path, the same table names are created in SQLite when absent. The validated current SQLite load was repeated successfully. PostgreSQL itself was not available in the local verification environment, so a PostgreSQL connection and constraint-preservation check remain an environment-specific demonstration step.

Automated tests cover the SQLite fallback, generated encounter/admission/diagnosis/patient marts, identical-baseline drift behavior, API startup and prediction, and disjoint patient groups across model partitions. The focused suite passed all seven tests. A full repository-wide pytest collection is not used because the project contains an inaccessible generated Airflow `dag_processor/latest` entry; running pytest against `tests/` avoids treating generated logs as source tests.

## 13. Model Metrics and Their Meaning

The selected XGBoost model's held-out test precision of 0.610 means about 61% of its positive predictions match the dataset-defined positive class in this split. Recall of 0.624 means about 62% of actual positive-class encounters were identified at the default 0.5 cutoff. F1 of 0.617 summarizes the precision-recall balance at that cutoff. These metrics are threshold dependent and do not establish that the threshold is appropriate for a clinical workflow.

ROC-AUC of 0.695 measures ranking discrimination over possible thresholds rather than correctness at one operating point. Brier score of 0.221 is the mean squared difference between predicted probabilities and observed binary labels, where lower is better. Brier score is a useful probabilistic accuracy measure, but by itself it does not show whether probabilities are calibrated within every risk range or subgroup. Reliability plots, confidence intervals, external validation, and decision-curve analysis would be appropriate next analyses before considering any operational use.

The monitoring utility was also run with the same 101,766-row dataset as both baseline and current data. As expected, all feature PSI values were zero and no missingness alerts fired. On this full cohort, the fitted model yielded precision 0.613, recall 0.630, F1 0.621, and Brier score 0.218. Those are in-sample monitoring values, not a second test result, and are therefore not substituted for the held-out metrics above. The utility reports metrics separately for race, gender, and age groups with at least 30 rows; these descriptive subgroup metrics are a screening aid, not a fairness certification. In particular, a minimum group size does not remove uncertainty or resolve the ethical implications of using demographic predictors.

## 14. Reproducibility, Operations, and Retraining

Use a controlled Python environment and record the actual dependency versions used for any submitted rerun. The included requirements list describes needed packages, while Airflow's own installation should follow its official constraints for the chosen Python/platform combination. Dataset acquisition remains a separate explicit step: the project does not download data from an unverified mirror and does not alter the original raw CSVs. Random seeds are set for the grouped splits and each candidate estimator. MLflow's local SQLite tracking store and model registry provide parameters, metrics, artifacts, run lineage, and model version history on this machine.

The API health response distinguishes a loaded model from a missing artifact. Request monitoring reports aggregate request count, failure count, and average latency; it intentionally does not write request feature values to logs. The batch report measures feature missingness and PSI and can evaluate labeled records after outcomes become available. The current report's PSI threshold of 0.2 is a conventional alert heuristic for this coursework implementation, not a universally validated threshold. It should trigger investigation, not automatic deployment or automatic retraining.

A responsible retraining proposal would first confirm that the incoming data comes from an approved source, passes schema and missingness rules, and has mature labels that match the target definition. A sustained feature drift alert or deterioration in recall, F1, or Brier score over a sufficiently large labeled cohort could initiate review. The review would inspect subgroup outcomes and potential data-pipeline changes, then compare a candidate retrain against the frozen evaluation protocol and current registered model. Promotion would require documented approval, reproducible artifacts, and a rollback path. No model is automatically promoted by the supplied scripts.

Docker packaging copies only the inference service, its runtime requirements, and the trained model artifact; raw input data, staging files, and local Airflow history are excluded from its build context. The image could not be built in the current environment because Docker CLI/engine is unavailable. The Dockerfile uses Python 3.13 to match the local model-training interpreter, but a real image build should also pin package versions to the MLflow run's environment and test model deserialization before distribution.

## 15. Demonstration Record and Remaining Submission Work

The current verification run regenerated staging, cleaned, and analytical layers from the provided raw data; wrote all four analytical marts; loaded the local SQLite development database; trained and registered an MLflow model; exercised labeled drift and subgroup monitoring; and passed seven automated tests. The dashboard was started locally at `http://127.0.0.1:8501/`. A browser smoke test confirmed that the summary metrics and risk form render, and submitting a synthetic example displayed a probability. No real patient data was entered into the form.

The repository already contains Airflow task logs from earlier successful runs. This verification run executed the ETL script directly rather than triggering Airflow again, so students should still capture a fresh Airflow run in their submission environment and verify the PostgreSQL target if their instructor requires it. Dashboard and execution screenshots should be captured and placed in the submission package after that demonstration. The Docker image build also remains pending installation of Docker. These limitations are explicit so the report distinguishes completed local evidence from environment-dependent deliverables.
