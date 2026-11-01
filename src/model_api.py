"""Local inference API for the academic readmission-risk prototype."""

import logging
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

ROOT_DIR = Path(__file__).resolve().parent.parent
MODEL_PATH = Path(os.getenv(
    "READMISSION_MODEL_PATH", ROOT_DIR / "models" / "readmission_model.joblib"
))
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("readmission_api")
model = None
request_count = 0
failure_count = 0
total_latency_ms = 0.0


class ReadmissionFeatures(BaseModel):
    race: str = Field(min_length=1, max_length=50)
    gender: str = Field(min_length=1, max_length=20)
    age: str = Field(min_length=1, max_length=20)
    admission_type_id: int = Field(ge=1, le=8)
    discharge_disposition_id: int = Field(ge=1, le=30)
    admission_source_id: int = Field(ge=1, le=26)
    length_of_stay: int = Field(ge=1, le=365)
    prior_admissions: int = Field(ge=0)
    diagnosis_count: int = Field(ge=0, le=16)
    medication_count: int = Field(ge=0, le=100)


@asynccontextmanager
async def lifespan(_app):
    global model
    if MODEL_PATH.exists():
        model = joblib.load(MODEL_PATH)
    yield


app = FastAPI(
    title="Hospital Readmission Risk Prototype",
    description="Academic decision-support prototype; not for clinical use.",
    version="1.0.0",
    lifespan=lifespan,
)


@app.middleware("http")
async def record_request_metrics(request: Request, call_next):
    global request_count, failure_count, total_latency_ms
    started = time.perf_counter()
    try:
        response = await call_next(request)
        if response.status_code >= 500:
            failure_count += 1
        return response
    except Exception:
        failure_count += 1
        raise
    finally:
        elapsed = (time.perf_counter() - started) * 1000
        request_count += 1
        total_latency_ms += elapsed
        logger.info(
            "request method=%s path=%s duration_ms=%.2f failures=%d",
            request.method, request.url.path, elapsed, failure_count,
        )


@app.get("/health")
def health():
    return {"status": "ready" if model is not None else "model_not_loaded"}


@app.get("/metrics")
def metrics():
    return {
        "requests": request_count,
        "failures": failure_count,
        "average_latency_ms": total_latency_ms / request_count if request_count else 0,
    }


@app.post("/predict")
def predict(features: ReadmissionFeatures):
    if model is None:
        raise HTTPException(
            status_code=503,
            detail="Model artifact is unavailable. Train the model before serving.",
        )
    row = pd.DataFrame([features.model_dump()])
    probability = float(model.predict_proba(row)[0, 1])
    return {
        "readmission_risk_probability": round(probability, 6),
        "risk_threshold": 0.5,
        "above_threshold": probability >= 0.5,
        "intended_use": "Academic decision-support prototype; not for clinical use.",
    }
