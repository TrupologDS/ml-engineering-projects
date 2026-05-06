"""Evaluate the trained CatBoost price model with cross-validation and holdout metrics."""

from __future__ import annotations

import json
import os

import joblib
import pandas as pd
import yaml
from catboost import CatBoostRegressor
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import KFold, cross_validate
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


def make_pipeline(params: dict) -> Pipeline:
    train_params = params["train"]
    num_pipeline = Pipeline(
        [("imputer", SimpleImputer(strategy="median")), ("scaler", StandardScaler())]
    )
    cat_pipeline = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("ohe", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
        ]
    )
    preprocessor = ColumnTransformer(
        [
            ("num", num_pipeline, train_params["preprocess"]["num_cols"]),
            ("cat", cat_pipeline, train_params["preprocess"]["cat_cols"]),
        ]
    )
    return Pipeline(
        [
            ("prep", preprocessor),
            ("model", CatBoostRegressor(**train_params["catboost"], verbose=False)),
        ]
    )


def evaluate_model() -> None:
    with open("params.yaml", encoding="utf-8") as fd:
        params = yaml.safe_load(fd)

    evaluate_params = params["evaluate"]
    target_col = evaluate_params["target_col"]
    drop_cols = evaluate_params["drop_cols"]
    train_df = pd.read_csv("data/train_data.csv")
    test_df = pd.read_csv("data/test_data.csv")

    x_train = train_df.drop(columns=drop_cols + [target_col])
    y_train = train_df[target_col]
    x_test = test_df.drop(columns=drop_cols + [target_col])
    y_test = test_df[target_col]

    cv = KFold(**evaluate_params["cv"])
    cv_results = cross_validate(
        make_pipeline(params),
        x_train,
        y_train,
        cv=cv,
        scoring=evaluate_params["metrics"],
        return_train_score=False,
    )
    os.makedirs("cv_results", exist_ok=True)
    with open("cv_results/cv_results.json", "w", encoding="utf-8") as fd:
        json.dump(
            {
                metric: cv_results[f"test_{metric}"].tolist()
                for metric in evaluate_params["metrics"]
            },
            fd,
            indent=4,
        )

    fitted_pipeline = joblib.load("models/catboost_pipe.pkl")
    y_pred = fitted_pipeline.predict(x_test)
    test_metrics = {
        "MAE": mean_absolute_error(y_test, y_pred),
        "RMSE": mean_squared_error(y_test, y_pred) ** 0.5,
        "R2": r2_score(y_test, y_pred),
    }
    os.makedirs("metrics", exist_ok=True)
    with open("metrics/test_metrics.json", "w", encoding="utf-8") as fd:
        json.dump(test_metrics, fd, indent=4)


if __name__ == "__main__":
    evaluate_model()
