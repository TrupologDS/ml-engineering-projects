"""Airflow DAG that prepares the real estate modeling table."""

from __future__ import annotations

import pendulum
from airflow.decorators import dag, task
from steps.messages import send_telegram_failure_message, send_telegram_success_message


@dag(
    schedule="@once",
    start_date=pendulum.datetime(2025, 6, 28, tz="UTC"),
    catchup=False,
    tags=["etl", "real-estate"],
    on_success_callback=send_telegram_success_message,
    on_failure_callback=send_telegram_failure_message,
)
def clean_building_flats():
    """Deduplicate, impute, and trim outliers before model training."""

    @task()
    def create_table() -> None:
        from airflow.providers.postgres.hooks.postgres import PostgresHook
        from sqlalchemy import (
            Column,
            Float,
            Integer,
            MetaData,
            String,
            Table,
            UniqueConstraint,
            inspect,
        )

        hook = PostgresHook("destination_db")
        engine = hook.get_sqlalchemy_engine()
        metadata = MetaData()
        clean_table = Table(
            "clean_building_flats",
            metadata,
            Column("id", Integer, primary_key=True, autoincrement=True),
            Column("building_id", String, nullable=False),
            Column("flat_id", Integer, nullable=False),
            Column("build_year", Integer),
            Column("building_type_int", Integer),
            Column("latitude", Float),
            Column("longitude", Float),
            Column("ceiling_height", Float),
            Column("flats_count", Integer),
            Column("floors_total", Integer),
            Column("has_elevator", Integer),
            Column("floor", Integer),
            Column("kitchen_area", Float),
            Column("living_area", Float),
            Column("rooms", Integer),
            Column("is_apartment", Integer),
            Column("studio", Integer),
            Column("total_area", Float),
            Column("price", Float),
            UniqueConstraint("building_id", "flat_id", name="uix_clean_building_flats"),
        )

        if not inspect(engine).has_table(clean_table.name):
            metadata.create_all(engine)
        engine.dispose()

    @task()
    def extract():
        import pandas as pd
        from airflow.providers.postgres.hooks.postgres import PostgresHook

        hook = PostgresHook("destination_db")
        with hook.get_conn() as conn:
            return pd.read_sql("SELECT * FROM building_flats", conn).drop(columns=["id"])

    @task()
    def transform(df):
        import pandas as pd

        feature_cols = df.columns.drop(["building_id", "flat_id"])
        df = df[~df.duplicated(subset=feature_cols, keep=False)].reset_index(drop=True)

        cols_with_missing = df.columns[df.isnull().any()]
        for col in cols_with_missing:
            if pd.api.types.is_numeric_dtype(df[col]):
                fill_value = df[col].mean()
            else:
                fill_value = df[col].mode().iat[0]
            df[col] = df[col].fillna(fill_value)

        num_cols = df.select_dtypes(include=["number"]).columns
        outliers = pd.Series(False, index=df.index)
        for col in num_cols:
            q1, q3 = df[col].quantile([0.25, 0.75])
            iqr = q3 - q1
            lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
            outliers |= ~df[col].between(lower, upper)
        return df[~outliers].reset_index(drop=True)

    @task()
    def load(df) -> None:
        from airflow.providers.postgres.hooks.postgres import PostgresHook

        hook = PostgresHook("destination_db")
        hook.insert_rows(
            table="clean_building_flats",
            rows=df.values.tolist(),
            target_fields=df.columns.tolist(),
            replace=True,
            replace_index=["building_id", "flat_id"],
        )

    create_table()
    raw_data = extract()
    cleaned_data = transform(raw_data)
    load(cleaned_data)


dag = clean_building_flats()
