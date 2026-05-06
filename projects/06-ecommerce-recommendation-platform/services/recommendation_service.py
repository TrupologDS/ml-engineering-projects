"""E-commerce recommendation service with offline, online, and blended routes."""

from __future__ import annotations

import logging
import os
import time
from contextlib import asynccontextmanager

import pandas as pd
import requests
from fastapi import FastAPI, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

REQUESTS = Counter("rec_requests_total", "Request count", ["route"])
LATENCY = Histogram("rec_latency_seconds", "Latency in seconds", ["route"])
FALLBACKS = Counter("rec_default_fallback_total", "Default fallback count")
ERRORS = Counter("rec_errors_total", "Error count", ["route"])

logger = logging.getLogger("uvicorn.error")
FEATURES_URL = os.getenv("FEATURES_URL", "http://127.0.0.1:8010")
EVENTS_URL = os.getenv("EVENTS_URL", "http://127.0.0.1:8020")


class RecStore:
    """Load and serve offline recommendations and default top items."""

    def __init__(self) -> None:
        self.personal: pd.DataFrame | None = None
        self.default: pd.DataFrame | None = None

    def load(self) -> None:
        self.personal = pd.read_parquet("models/final_recommendations_feat.parquet").set_index(
            "user_id"
        )
        self.default = pd.read_parquet("models/top_recs.parquet")

    def has_personal(self, user_id: int) -> bool:
        if self.personal is None:
            return False
        try:
            self.personal.loc[user_id]
            return True
        except KeyError:
            return False

    def get_offline(self, user_id: int, k: int) -> list[int]:
        if self.personal is None or self.default is None:
            return []
        try:
            values = self.personal.loc[user_id]["item_id"]
            return values.tolist()[:k]
        except KeyError:
            return self.default["item_id"].tolist()[:k]


def dedup(seq: list[int]) -> list[int]:
    seen: set[int] = set()
    out: list[int] = []
    for item_id in seq:
        if item_id in seen:
            continue
        seen.add(item_id)
        out.append(item_id)
    return out


store = RecStore()


@asynccontextmanager
async def lifespan(app: FastAPI):
    store.load()
    logger.info("Recommendations ready")
    yield


app = FastAPI(title="recommendations", lifespan=lifespan)


@app.post("/recommendations_offline")
async def recommendations_offline(user_id: int, k: int = 100) -> dict[str, list[int]]:
    start = time.perf_counter()
    try:
        recs = store.get_offline(user_id, k)
        if not store.has_personal(user_id):
            FALLBACKS.inc()
        return {"recs": recs}
    except Exception as exc:
        logger.error("Offline recommendation error: %s", exc)
        ERRORS.labels("/recommendations_offline").inc()
        return {"recs": []}
    finally:
        LATENCY.labels("/recommendations_offline").observe(time.perf_counter() - start)
        REQUESTS.labels("/recommendations_offline").inc()


@app.post("/recommendations_online")
async def recommendations_online(user_id: int, k: int = 100) -> dict[str, list[int]]:
    start = time.perf_counter()
    try:
        last_response = requests.post(
            f"{EVENTS_URL}/get",
            params={"user_id": user_id, "k": 3},
            timeout=3,
        )
        last_response.raise_for_status()
        last_items = last_response.json().get("events", []) or []

        # Recent user events drive an online similarity lookup.
        items: list[int] = []
        scores: list[float] = []
        for item_id in last_items:
            try:
                response = requests.post(
                    f"{FEATURES_URL}/similar_items",
                    params={"item_id": item_id, "k": k},
                    timeout=3,
                )
                response.raise_for_status()
                body = response.json()
                items += body.get("item_id_2", []) or []
                scores += body.get("score", []) or []
            except Exception as exc:
                logger.warning("Feature service failed for item %s: %s", item_id, exc)
                ERRORS.labels("/recommendations_online").inc()

        ranked = sorted(zip(items, scores, strict=False), key=lambda x: x[1], reverse=True)
        return {"recs": dedup([item_id for item_id, _ in ranked])[:k]}
    except Exception as exc:
        logger.error("Online recommendation error: %s", exc)
        ERRORS.labels("/recommendations_online").inc()
        return {"recs": []}
    finally:
        LATENCY.labels("/recommendations_online").observe(time.perf_counter() - start)
        REQUESTS.labels("/recommendations_online").inc()


@app.post("/recommendations")
async def recommendations(user_id: int, k: int = 100) -> dict[str, list[int]]:
    start = time.perf_counter()
    try:
        offline = (await recommendations_offline(user_id, k))["recs"]
        online = (await recommendations_online(user_id, k))["recs"]
        mixed: list[int] = []
        # Interleave fresh online items with stable offline recommendations.
        for online_item, offline_item in zip(online, offline, strict=False):
            mixed += [online_item, offline_item]
        mixed += online[len(offline) :] + offline[len(online) :]
        return {"recs": dedup(mixed)[:k]}
    except Exception as exc:
        logger.error("Blending error: %s", exc)
        ERRORS.labels("/recommendations").inc()
        return {"recs": []}
    finally:
        LATENCY.labels("/recommendations").observe(time.perf_counter() - start)
        REQUESTS.labels("/recommendations").inc()


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/metrics")
async def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
