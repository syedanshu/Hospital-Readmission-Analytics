import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError


ROOT_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT_DIR / ".env"


def _load_project_env():
    if ENV_PATH.exists():
        load_dotenv(dotenv_path=ENV_PATH, override=False)


def get_database_url():
    _load_project_env()

    user = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")
    host = os.getenv("DB_HOST")
    port = os.getenv("DB_PORT")
    database = os.getenv("DB_NAME")

    configured = all(
        value not in (None, "", "YOUR_PASSWORD", "your_password")
        for value in (user, password, host, port, database)
    )

    if configured:
        postgres_url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}"
        try:
            create_engine(postgres_url).connect()
            return postgres_url
        except OperationalError:
            pass

    sqlite_path = ROOT_DIR / "data" / "local_hospital_readmission.db"
    return f"sqlite:///{sqlite_path}"
