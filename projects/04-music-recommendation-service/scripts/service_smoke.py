"""Manual smoke scenarios for the recommendation microservices."""

from __future__ import annotations

import json
import os
import time

import pandas as pd
import requests

REC_URL = os.getenv("REC_URL", "http://127.0.0.1:8000")
EVT_URL = os.getenv("EVT_URL", "http://127.0.0.1:8020")
FINAL_PATH = "recsys/recommendations/recommendations.parquet"
TOP_PATH = "recsys/recommendations/top_popular.parquet"
SIM_PATH = "recsys/recommendations/similar.parquet"
LOG_PATH = "service_smoke_test.log"


def log(message: str, data: dict | None = None) -> None:
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}"
    if data is not None:
        line += " " + json.dumps(data, ensure_ascii=False)[:1000]
    print(line)
    with open(LOG_PATH, "a", encoding="utf-8") as fd:
        fd.write(line + "\n")


def safe_post(url: str, params: dict) -> tuple[int, dict]:
    try:
        response = requests.post(url, params=params, timeout=5.0)
        return response.status_code, response.json()
    except Exception as exc:
        return 0, {"error": str(exc)}


def main() -> None:
    open(LOG_PATH, "w", encoding="utf-8").close()
    final_df = pd.read_parquet(FINAL_PATH, columns=["user_id", "item_id", "rank"])
    top_df = pd.read_parquet(TOP_PATH, columns=["item_id", "rank"])
    sim = pd.read_parquet(SIM_PATH, columns=["item_id_1"]).drop_duplicates().head(3)
    user_with_personal = int(final_df["user_id"].iloc[0])
    user_without_personal = int(final_df["user_id"].max()) + 123

    log("Artifacts loaded", {"final_rows": int(len(final_df)), "top_rows": int(len(top_df))})
    for item_id in sim["item_id_1"].tolist():
        requests.post(
            f"{EVT_URL}/put",
            params={"user_id": user_with_personal, "item_id": int(item_id)},
            timeout=3.0,
        )

    for label, user_id in [
        ("cold_user", user_without_personal),
        ("warm_user", user_with_personal),
    ]:
        for route in ["recommendations_offline", "recommendations_online", "recommendations"]:
            status, body = safe_post(f"{REC_URL}/{route}", {"user_id": user_id, "k": 10})
            log(label, {"route": route, "status": status, "head": body.get("recs", [])[:5]})


if __name__ == "__main__":
    main()
