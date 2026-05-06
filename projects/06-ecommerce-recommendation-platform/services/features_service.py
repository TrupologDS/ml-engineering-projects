"""Item similarity feature service with Prometheus metrics."""

from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager

import pandas as pd
from fastapi import FastAPI, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

logger = logging.getLogger("uvicorn.error")
REQUESTS = Counter("features_requests_total", "Request count", ["route"])
LATENCY = Histogram("features_latency_seconds", "Latency in seconds", ["route"])


class SimilarItems:
    """Serve similar item rows from the model artifact directory."""

    def __init__(self) -> None:
        self.df: pd.DataFrame | None = None

    def load(self, path: str, **kwargs) -> None:
        logger.info("Loading similar items")
        self.df = pd.read_parquet(path, **kwargs).set_index("item_id_1")
        logger.info("Similar items ready")

    def get(self, item_id: int, k: int = 10) -> dict[str, list]:
        if self.df is None:
            return {"item_id_2": [], "score": []}
        try:
            data = self.df.loc[item_id].head(max(0, k))
            return {"item_id_2": data["item_id_2"].tolist(), "score": data["score"].tolist()}
        except KeyError:
            return {"item_id_2": [], "score": []}


store = SimilarItems()


@asynccontextmanager
async def lifespan(app: FastAPI):
    store.load("models/similar_items.parquet", columns=["item_id_1", "item_id_2", "score"])
    yield


app = FastAPI(title="features", lifespan=lifespan)


@app.post("/similar_items")
async def similar_items(item_id: int, k: int = 10) -> dict[str, list]:
    start = time.perf_counter()
    try:
        return store.get(item_id, k)
    finally:
        LATENCY.labels("/similar_items").observe(time.perf_counter() - start)
        REQUESTS.labels("/similar_items").inc()


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/metrics")
async def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
