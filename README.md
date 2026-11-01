# Hospital Readmission Analytics and Risk Prototype

This project implements a reproducible ETL and Streamlit dashboard, with an academic MLOps extension for readmission-risk experiments and local inference.

## Dataset

Primary source: [UCI Diabetes 130-US Hospitals for Years 1999-2008](https://archive.ics.uci.edu/dataset/296/diabetes+130-us+hospitals+for+years+1999-2008). The dataset is de-identified and publicly accessible through the UCI Machine Learning Repository. Open the dataset page, review its citation/access terms, and download the archive. Place the original files:

Place:
- `diabetic_data.csv`
- `IDS_mapping.csv`

inside `data/raw/`.

Do not use real patient data. MIMIC-IV is not used because it requires credentialed access and separate data-use compliance. See [the data dictionary](docs/data_dictionary.md) for dataset limitations and privacy notes.

## Setup

Create a virtual environment:

```bash
python -m venv .venv
```

Activate on Windows:

```bash
.venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Airflow requires its supported Python version and constraints for reliable installation. Follow the official Apache Airflow installation instructions for your platform if installing Airflow separately; the application scripts and dashboard can run without starting Airflow.

Copy `.env.example` to `.env` and enter PostgreSQL credentials.

## Run ETL

From the project root:

```bash
python src/pipeline.py
```

Outputs are regenerated in `data/staging/`, `data/cleaned/`, and `data/analytical/`. Source CSVs remain in `data/raw/`; status, failure, and rejected-row records are under `logs/`.

Run the automated tests with:

```bash
python -m pytest tests -q
```

## PostgreSQL

Create a database named `hospital_readmission`.

Run `database/schema.sql` in PostgreSQL, then:

```bash
python src/load_postgres.py
```

When PostgreSQL is not configured or reachable, the project uses `data/local_hospital_readmission.db` (SQLite) for local development. Configure `.env` using `.env.example` when targeting PostgreSQL.

## Dashboard

```bash
streamlit run dashboard/app.py
```

The dashboard has summary indicators and seven views, including readmission by age and primary diagnosis, admission-type comparisons, readmission class, length of stay, diagnosis count, and medication count. After model training, it also exposes an optional risk-estimate form. The source has no department field, so admission type is used rather than an invented department classification.

## Part 1 pipeline

Dataset -> ingestion -> raw/staging -> cleaning -> validation -> analytical data -> PostgreSQL -> Streamlit dashboard.

Airflow is used to orchestrate the same ETL workflow. On Windows, run Airflow in WSL2 (native Windows execution is unsupported). The launcher sets the correct project DAG folder, project root, a SQLite-compatible executor, disables example DAGs, and uses `airflow_home/airflow_project.db` for project metadata. The existing `airflow_home/airflow.db` is left untouched.

In PowerShell, enter Ubuntu:

```powershell
wsl -d Ubuntu
```

You already have Airflow in the WSL environment at `$HOME/.venvs/hospital_readmission`. Activate it and list the project DAG:

```bash
cd "/mnt/c/Users/syed anshu/Downloads/hospital_readmission_project"
source "$HOME/.venvs/hospital_readmission/bin/activate"
bash scripts/run_airflow.sh dags list
```

If Airflow is not installed in a different WSL environment, install it in a dedicated virtual environment using the matching official constraints:

```bash
python3 -m venv "$HOME/.venvs/hospital-airflow"
source "$HOME/.venvs/hospital-airflow/bin/activate"
AIRFLOW_VERSION=3.3.1
PYTHON_VERSION="$(python -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
CONSTRAINT_URL="https://raw.githubusercontent.com/apache/airflow/constraints-${AIRFLOW_VERSION}/constraints-${PYTHON_VERSION}.txt"
pip install "apache-airflow==${AIRFLOW_VERSION}" --constraint "${CONSTRAINT_URL}"
pip install pandas python-dotenv psycopg2-binary
```

Start the standalone Airflow services only if they are not already running:

```bash
bash scripts/run_airflow.sh
```

Keep that terminal open. The Airflow UI is at `http://localhost:8080`. In a second WSL terminal, activate the same environment, enter the project directory, and check or trigger the DAG:

```bash
cd "/mnt/c/Users/syed anshu/Downloads/hospital_readmission_project"
source "$HOME/.venvs/hospital-airflow/bin/activate"
bash scripts/run_airflow.sh dags list
bash scripts/run_airflow.sh dags trigger hospital_readmission_etl
```

The DAG uses a daily schedule and can also be triggered manually in the UI. Task logs are retained under `airflow_home/logs/`.

## MLOps Extension

Train the three candidate models and register the validation-selected model:

```bash
python -m src.train_model
```

Training writes held-out metrics, metadata, and feature importance under `models/`, and records parameters, metrics, artifacts, and the registered model version in MLflow. The reproducible split groups by patient because the dataset has repeated encounters but no event timestamp. The target is the dataset-defined `NO` versus either readmission class, not strictly 30-day readmission.

Run the local inference service:

```bash
uvicorn src.model_api:app --host 127.0.0.1 --port 8000
```

Use `/health`, `/metrics`, and `POST /predict`. The API is an academic decision-support prototype only and must not be used for clinical decisions. For a container build, train first so the model file exists, then run `docker build -t hospital-readmission-api .` and `docker run --rm -p 8000:8000 hospital-readmission-api`.

Compare a later feature extract to the training baseline and optionally evaluate a labeled extract:

```bash
python -m src.monitor_data --current path/to/current_features.csv
python -m src.monitor_data --current path/to/labeled_features.csv --labeled
```

The monitor writes `logs/drift_report.json`, including missingness, PSI drift alerts, and (when labels are supplied) precision, recall, F1, and Brier score. Start MLflow's local UI with `mlflow ui --backend-store-uri sqlite:///mlflow.db`.

## Submission Material

- Architecture: [docs/architecture.md](docs/architecture.md)
- Data dictionary and validation rules: [docs/data_dictionary.md](docs/data_dictionary.md)
- Project report: [docs/project_report.md](docs/project_report.md)
- Airflow execution logs: `airflow_home/logs/`

Capture fresh screenshots of the pipeline run and dashboard locally for the submission; no screenshots are represented as included unless actually saved in the project.
