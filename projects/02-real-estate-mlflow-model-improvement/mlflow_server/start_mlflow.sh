#!/usr/bin/env bash
set -euo pipefail

# Load local environment variables.
source "$(dirname "$0")/.env"

echo "Migrating MLflow DB schema..."
mlflow db upgrade "${DB_URI}"

echo "Starting MLflow Tracking Server..."
mlflow server \
  --backend-store-uri   "${DB_URI}" \
  --default-artifact-root "${ARTIFACT_ROOT}" \
  --host 0.0.0.0 --port 5000
