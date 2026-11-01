from unittest.mock import patch

from sqlalchemy.exc import OperationalError

import src.db_utils as db_utils


def test_sqlite_fallback_when_postgres_not_configured(monkeypatch, tmp_path):
    for key in [
        "DB_HOST",
        "DB_PORT",
        "DB_NAME",
        "DB_USER",
        "DB_PASSWORD",
    ]:
        monkeypatch.delenv(key, raising=False)

    monkeypatch.setattr(db_utils, "ENV_PATH", tmp_path / ".env")

    assert db_utils.get_database_url().startswith("sqlite:///")


def test_sqlite_fallback_when_postgres_connection_refused(monkeypatch):
    monkeypatch.setenv("DB_HOST", "localhost")
    monkeypatch.setenv("DB_PORT", "5432")
    monkeypatch.setenv("DB_NAME", "hospital_readmission")
    monkeypatch.setenv("DB_USER", "postgres")
    monkeypatch.setenv("DB_PASSWORD", "postgres")

    with patch("src.db_utils.create_engine") as mock_create_engine:
        mock_create_engine.return_value.connect.side_effect = OperationalError(
            "statement",
            "params",
            "connection refused",
        )

        assert db_utils.get_database_url().startswith("sqlite:///")


def test_db_utils_loads_project_dotenv(monkeypatch, tmp_path):
    for key in [
        "DB_HOST",
        "DB_PORT",
        "DB_NAME",
        "DB_USER",
        "DB_PASSWORD",
    ]:
        monkeypatch.delenv(key, raising=False)

    env_file = tmp_path / ".env"
    env_file.write_text(
        "DB_HOST=localhost\n"
        "DB_PORT=5432\n"
        "DB_NAME=hospital_readmission\n"
        "DB_USER=postgres\n"
        "DB_PASSWORD=postgres\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(db_utils, "ENV_PATH", env_file)

    with patch("src.db_utils.load_dotenv") as mock_load_dotenv:
        monkeypatch.setenv("DB_HOST", "localhost")
        monkeypatch.setenv("DB_PORT", "5432")
        monkeypatch.setenv("DB_NAME", "hospital_readmission")
        monkeypatch.setenv("DB_USER", "postgres")
        monkeypatch.setenv("DB_PASSWORD", "postgres")

        with patch("src.db_utils.create_engine") as mock_create_engine:
            mock_create_engine.return_value.connect.return_value = object()
            assert db_utils.get_database_url().startswith("postgresql+psycopg2://")

        mock_load_dotenv.assert_called_once_with(dotenv_path=env_file, override=False)
