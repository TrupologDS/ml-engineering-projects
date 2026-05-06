"""Split the real estate dataset into train and test partitions."""

from __future__ import annotations

import os

import pandas as pd
import yaml
from sklearn.model_selection import train_test_split


def split_data() -> None:
    with open("params.yaml", encoding="utf-8") as fd:
        params = yaml.safe_load(fd)

    index_col = params["index_col"]
    df = pd.read_csv("data/initial_data.csv", index_col=index_col)
    train_df, test_df = train_test_split(
        df,
        test_size=params["test_size"],
        random_state=42,
        shuffle=True,
    )

    os.makedirs("data", exist_ok=True)
    train_df.to_csv("data/train_data.csv", index_label=index_col)
    test_df.to_csv("data/test_data.csv", index_label=index_col)


if __name__ == "__main__":
    split_data()
