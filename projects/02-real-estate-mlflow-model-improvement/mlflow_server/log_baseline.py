"""Log a baseline real estate price model to MLflow."""

from __future__ import annotations

import os

import joblib
import mlflow
import mlflow.sklearn
import pandas as pd
import yaml
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

EXPERIMENT_NAME = "real_estate_pricing"
MODEL_REGISTRY_NAME = "real_estate_price_model"
BASE_DIR = "baseline"
MODEL_PATH = os.path.join(BASE_DIR, "catboost_pipe.pkl")
TEST_PATH = os.path.join(BASE_DIR, "test_data.csv")
PARAMS_PATH = os.path.join(BASE_DIR, "params.yaml")


def main() -> None:
    df_test = pd.read_csv(TEST_PATH)
    with open(PARAMS_PATH, encoding="utf-8") as fd:
        params = yaml.safe_load(fd)

    target_col = params["train"]["target_col"]
    y_test = df_test[target_col]
    x_test = df_test.drop(columns=params["train"]["drop_cols"] + [target_col])

    model = joblib.load(MODEL_PATH)
    preds = model.predict(x_test)
    metrics = {
        "rmse": mean_squared_error(y_test, preds, squared=False),
        "mae": mean_absolute_error(y_test, preds),
        "r2": r2_score(y_test, preds),
    }

    mlflow.set_tracking_uri(os.environ["MLFLOW_TRACKING_URI"])
    mlflow.set_experiment(EXPERIMENT_NAME)
    with mlflow.start_run(run_name="baseline_v1") as run:
        mlflow.log_params({"model_type": "CatBoostRegressor", **params["train"]["catboost"]})
        mlflow.log_params({"n_test_rows": len(x_test)})
        mlflow.log_metrics(metrics)
        mlflow.sklearn.log_model(
            sk_model=model,
            artifact_path="model",
            registered_model_name=MODEL_REGISTRY_NAME,
            input_example=x_test.head(3),
        )
        print(f"Logged baseline run to MLflow: {run.info.run_id}")


if __name__ == "__main__":
    main()
