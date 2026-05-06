# Real Estate Model Improvement with MLflow

This project improves a baseline flat price model and tracks experiments, metrics, parameters, and registered model versions in MLflow.

## Overview
- Business context: improve pricing accuracy for real estate listings.
- ML problem type: supervised regression.
- Final deliverable: an MLflow-tracked CatBoost model improvement workflow.

## ML Task
- Target variable: `price`.
- Input features: building metadata, location, apartment floor/area/room attributes, and engineered features.
- Evaluation metrics: RMSE, MAE, and R2.
- Assumptions: baseline train/test data and model artifacts are available locally or from private storage.

## Data
Raw train/test CSV files and model binaries are excluded. The public repository keeps only safe parameters and code. Reproduction requires configured access to the private artifact store or regenerated data from the upstream DVC pipeline.

## Solution Architecture
```mermaid
flowchart LR
    A[Baseline artifacts] --> B[MLflow baseline logging]
    B --> C[EDA]
    C --> D[Feature engineering]
    D --> E[Feature selection]
    E --> F[Optuna and random search]
    F --> G[MLflow model registry]
```

## Repository Structure
```text
.
|-- baseline/
|   `-- params.yaml
|-- docs/
|-- mlflow_server/
|   |-- .env.example
|   |-- log_baseline.py
|   `-- start_mlflow.sh
|-- notebooks/
`-- requirements.txt
```

## Tech Stack
Python, pandas, NumPy, scikit-learn, CatBoost, Optuna, mlxtend, MLflow, PostgreSQL, S3-compatible object storage.

## How to Run
```bash
cp mlflow_server/.env.example mlflow_server/.env
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
./mlflow_server/start_mlflow.sh
jupyter lab notebooks/real_estate_model_improvement.ipynb
```
Reproduction requires private data/model artifacts and configured MLflow backend and artifact storage.

## Pipeline Details
- `log_baseline.py` logs the baseline CatBoost pipeline to MLflow.
- The notebook compares engineered features, sequential feature selection, and hyperparameter search.
- MLflow stores run metrics, selected features, and model versions.

## Model Evaluation
Actual notebook-reported test metrics:
- Baseline: RMSE 2,364,520, MAE 1,843,910, R2 0.722.
- Custom features: RMSE 2,361,100, MAE 1,840,261, R2 0.723.
- Feature selection: RMSE 2,361,614, MAE 1,841,495, R2 0.723.
- Hyperparameter-tuned model: RMSE 2,290,669, MAE 1,766,209, R2 0.739.

## Engineering Highlights
- MLflow Tracking Server and model registry workflow.
- Experiment logging for model iterations and selected features.
- Hyperparameter optimization with Optuna and randomized search.
- Baseline artifacts excluded from GitHub and loaded from controlled storage.

## Limitations and Next Steps
- Add automated validation for feature schemas.
- Add a lightweight training script extracted from the notebook.
- Add model signature enforcement in MLflow.
- Add monitoring for prediction drift after deployment.
