FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    READMISSION_MODEL_PATH=/app/models/readmission_model.joblib

WORKDIR /app
COPY requirements-mlops.txt ./requirements-mlops.txt
RUN pip install --no-cache-dir -r requirements-mlops.txt
COPY src/__init__.py ./src/__init__.py
COPY src/model_api.py ./src/model_api.py
COPY models/ ./models/

EXPOSE 8000
CMD ["uvicorn", "src.model_api:app", "--host", "0.0.0.0", "--port", "8000"]
