#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export AIRFLOW_HOME="${AIRFLOW_HOME:-${PROJECT_DIR}/airflow_home}"
export AIRFLOW__CORE__DAGS_FOLDER="${PROJECT_DIR}/dags"
export AIRFLOW__CORE__EXECUTOR="${AIRFLOW__CORE__EXECUTOR:-SequentialExecutor}"
export AIRFLOW__CORE__LOAD_EXAMPLES="${AIRFLOW__CORE__LOAD_EXAMPLES:-False}"
export AIRFLOW__DATABASE__SQL_ALCHEMY_CONN="${AIRFLOW__DATABASE__SQL_ALCHEMY_CONN:-sqlite:///${AIRFLOW_HOME}/airflow_project.db}"
export HOSPITAL_PROJECT_DIR="${PROJECT_DIR}"

if ! command -v airflow >/dev/null 2>&1; then
    printf '%s\n' "Airflow CLI not found. Install Apache Airflow in your WSL Python environment first." >&2
    exit 127
fi

if (($# == 0)); then
    set -- standalone
fi

exec airflow "$@"
