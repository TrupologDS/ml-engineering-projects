"""Load the cleaned real estate table from PostgreSQL into the DVC workspace."""

from __future__ import annotations

import os

import pandas as pd
import psycopg2
import yaml
from dotenv import load_dotenv


def get_data() -> None:
    with open("params.yaml", encoding="utf-8") as fd:
        params = yaml.safe_load(fd)

    load_dotenv()
    # Database credentials are injected at runtime and are intentionally absent from GitHub.
    conn = psycopg2.connect(
        dbname=os.getenv("DB_DESTINATION_NAME"),
        user=os.getenv("DB_DESTINATION_USER"),
        password=os.getenv("DB_DESTINATION_PASSWORD"),
        host=os.getenv("DB_DESTINATION_HOST"),
        port=os.getenv("DB_DESTINATION_PORT"),
        sslmode=os.getenv("DB_SSLMODE", "require"),
    )
    try:
        data = pd.read_sql(
            "SELECT * FROM clean_building_flats",
            conn,
            index_col=params["index_col"],
        )
    finally:
        conn.close()

    os.makedirs("data", exist_ok=True)
    data.to_csv("data/initial_data.csv", index_label=params["index_col"])


if __name__ == "__main__":
    get_data()
