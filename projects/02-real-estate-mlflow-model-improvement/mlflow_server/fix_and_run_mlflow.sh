#!/usr/bin/env bash
set -euo pipefail

echo "Installing MLflow and PostgreSQL dependencies..."
pip install --upgrade "mlflow[sqlalchemy,boto3]" psycopg2-binary charset-normalizer

echo "Loading environment variables from .env"
source mlflow_server/.env

export DB_URI="${DB_URI}?sslmode=require"

echo "Running MLflow database migrations..."
mlflow db upgrade "${DB_URI}"

echo "Starting MLflow Tracking Server..."
mlflow server \
  --backend-store-uri "${DB_URI}" \
  --default-artifact-root "${ARTIFACT_ROOT}" \
  --host 0.0.0.0 \
  --port 5000
