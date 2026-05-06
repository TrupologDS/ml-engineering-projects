"""Update a Grafana dashboard JSON file with the current Prometheus datasource UID."""

from __future__ import annotations

import json
import os
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv("./services/.env")

GRAFANA_USER = os.getenv("GRAFANA_USER", "admin")
GRAFANA_PASS = os.getenv("GRAFANA_PASS")
DASHBOARD_PATH = os.getenv("GRAFANA_DASHBOARD_PATH", "monitoring/grafana-dashboard.json")
GRAFANA_URL = os.getenv("GRAFANA_URL", "http://localhost:3000")


def substitute_datasource_uid(dashboard: Any, current_uid: str) -> None:
    """Recursively replace Prometheus datasource UIDs in a Grafana dashboard."""
    if isinstance(dashboard, dict):
        for key, value in dashboard.items():
            if (
                key == "datasource"
                and isinstance(value, dict)
                and value.get("type") == "prometheus"
            ):
                value["uid"] = current_uid
            else:
                substitute_datasource_uid(value, current_uid)
    elif isinstance(dashboard, list):
        for item in dashboard:
            substitute_datasource_uid(item, current_uid)


def main() -> None:
    if not GRAFANA_PASS:
        raise RuntimeError("GRAFANA_PASS must be configured.")
    response = requests.get(
        f"{GRAFANA_URL}/api/datasources/1",
        auth=(GRAFANA_USER, GRAFANA_PASS),
        timeout=10,
    )
    response.raise_for_status()
    current_uid = response.json()["uid"]

    with open(DASHBOARD_PATH, encoding="utf-8") as fd:
        dashboard = json.load(fd)
    substitute_datasource_uid(dashboard, current_uid)
    with open(DASHBOARD_PATH, "w", encoding="utf-8") as fd:
        json.dump(dashboard, fd, indent=2)
    print("Grafana datasource UID updated.")


if __name__ == "__main__":
    main()
