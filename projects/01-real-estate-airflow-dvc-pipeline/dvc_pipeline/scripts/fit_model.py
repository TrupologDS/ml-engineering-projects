"""Train a CatBoost regression pipeline for flat price prediction."""

from __future__ import annotations

import os

import joblib
import pandas as pd
import yaml
from catboost import CatBoostRegressor
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


def fit_model() -> None:
    with open("params.yaml", encoding="utf-8") as fd:
        params = yaml.safe_load(fd)

    train_params = params["train"]
    df = pd.read_csv("data/train_data.csv")
    y = df[train_params["target_col"]]
    x = df.drop(columns=train_params["drop_cols"] + [train_params["target_col"]])

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
    model = CatBoostRegressor(**train_params["catboost"], verbose=False)
    pipeline = Pipeline([("prep", preprocessor), ("model", model)])
    pipeline.fit(x, y)

    os.makedirs("models", exist_ok=True)
    joblib.dump(pipeline, "models/catboost_pipe.pkl")


if __name__ == "__main__":
    fit_model()
