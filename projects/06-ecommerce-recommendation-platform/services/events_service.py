"""Online event store with Prometheus metrics."""

from __future__ import annotations

import time

from fastapi import FastAPI, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

REQUESTS = Counter("events_requests_total", "Request count", ["route"])
LATENCY = Histogram("events_latency_seconds", "Latency in seconds", ["route"])


class EventStore:
    """Keep recent user events in memory."""

    def __init__(self, max_events_per_user: int = 10) -> None:
        self.events: dict[int, list[int]] = {}
        self.max_events_per_user = max_events_per_user

    def put(self, user_id: int, item_id: int) -> None:
        history = self.events.get(user_id, [])
        self.events[user_id] = [item_id] + history[: self.max_events_per_user]

    def get(self, user_id: int, k: int = 10) -> list[int]:
        return self.events.get(user_id, [])[: max(0, k)]


events_store = EventStore()
app = FastAPI(title="events")


@app.post("/put")
async def put(user_id: int, item_id: int) -> dict[str, str]:
    start = time.perf_counter()
    try:
        events_store.put(user_id, item_id)
        return {"result": "ok"}
    finally:
        LATENCY.labels("/put").observe(time.perf_counter() - start)
        REQUESTS.labels("/put").inc()


@app.post("/get")
async def get(user_id: int, k: int = 10) -> dict[str, list[int]]:
    start = time.perf_counter()
    try:
        return {"events": events_store.get(user_id, k)}
    finally:
        LATENCY.labels("/get").observe(time.perf_counter() - start)
        REQUESTS.labels("/get").inc()


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/metrics")
async def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
