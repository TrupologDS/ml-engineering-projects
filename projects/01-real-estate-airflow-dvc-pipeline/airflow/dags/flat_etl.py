"""Airflow DAG that loads real estate source tables into a modeling table."""

from __future__ import annotations

import pendulum
from airflow.decorators import dag, task
from airflow.providers.postgres.hooks.postgres import PostgresHook
from steps.messages import send_telegram_failure_message, send_telegram_success_message


@dag(
    schedule="@once",
    start_date=pendulum.datetime(2025, 6, 28, tz="UTC"),
    catchup=False,
    tags=["etl", "real-estate"],
    on_success_callback=send_telegram_success_message,
    on_failure_callback=send_telegram_failure_message,
)
def flat_pricing_etl():
    """Extract flat and building data, normalize booleans, and load the target table."""

    @task()
    def create_table() -> None:
        from sqlalchemy import (
            Boolean,
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
        building_flats_table = Table(
            "building_flats",
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
            Column("has_elevator", Boolean),
            Column("floor", Integer),
            Column("kitchen_area", Float),
            Column("living_area", Float),
            Column("rooms", Integer),
            Column("is_apartment", Boolean),
            Column("studio", Boolean),
            Column("total_area", Float),
            Column("price", Float),
            UniqueConstraint("building_id", "flat_id", name="uix_building_flat"),
        )

        if not inspect(engine).has_table(building_flats_table.name):
            metadata.create_all(engine)
        engine.dispose()

    @task()
    def extract():
        import pandas as pd

        hook = PostgresHook("source_db")
        with hook.get_conn() as conn:
            return pd.read_sql(
                """
                SELECT
                    b.id AS building_id,
                    f.id AS flat_id,
                    b.build_year,
                    b.building_type_int,
                    b.latitude,
                    b.longitude,
                    b.ceiling_height,
                    b.flats_count,
                    b.floors_total,
                    b.has_elevator,
                    f.floor,
                    f.kitchen_area,
                    f.living_area,
                    f.rooms,
                    f.is_apartment,
                    f.studio,
                    f.total_area,
                    f.price
                FROM flats AS f
                JOIN buildings AS b ON b.id = f.building_id;
                """,
                conn,
            )

    @task()
    def transform(df):
        bool_cols = ["has_elevator", "is_apartment", "studio"]
        for col in bool_cols:
            df[col] = df[col].astype(str).str.lower().map({"true": 1, "false": 0}).astype("Int8")
        return df

    @task()
    def load(data) -> None:
        hook = PostgresHook("destination_db")
        hook.insert_rows(
            table="building_flats",
            rows=data.values.tolist(),
            target_fields=data.columns.tolist(),
            replace=True,
            replace_index=["building_id", "flat_id"],
        )

    create_table()
    raw_data = extract()
    transformed_data = transform(raw_data)
    load(transformed_data)


dag = flat_pricing_etl()
