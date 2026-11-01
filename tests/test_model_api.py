from fastapi.testclient import TestClient

from src.model_api import app


def test_prediction_api_loads_model_and_returns_probability():
    with TestClient(app) as client:
        health = client.get("/health")
        assert health.status_code == 200
        assert health.json()["status"] == "ready"

        response = client.post("/predict", json={
            "race": "Caucasian",
            "gender": "Female",
            "age": "[50-60)",
            "admission_type_id": 1,
            "discharge_disposition_id": 1,
            "admission_source_id": 7,
            "length_of_stay": 3,
            "prior_admissions": 1,
            "diagnosis_count": 5,
            "medication_count": 12,
        })
        assert response.status_code == 200
        result = response.json()
        assert 0 <= result["readmission_risk_probability"] <= 1
        assert result["intended_use"].startswith("Academic decision-support")
