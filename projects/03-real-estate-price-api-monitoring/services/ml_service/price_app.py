"""FastAPI application for online real estate price inference."""

from __future__ import annotations

import time

from fastapi import Body, FastAPI
from prometheus_client import Counter, Gauge, Histogram
from prometheus_fastapi_instrumentator import Instrumentator

from services.ml_service.fast_api_handler import FastApiHandler

app = FastAPI(title="Real Estate Price API", version="1.0.0")
app.handler = FastApiHandler()
Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)

REQUEST_COUNTER = Counter(
    "ml_inference_requests_total",
    "Inference requests by status",
    ["status"],
)
LATENCY_HIST = Histogram(
    "ml_inference_latency_seconds",
    "Inference request latency in seconds",
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)
MODEL_LOADED_GAUGE = Gauge("ml_model_loaded", "Model loaded flag: 1 loaded, 0 unavailable")
MODEL_LOADED_GAUGE.set(1.0 if getattr(app.handler, "model", None) is not None else 0.0)

USER_ID_BODY = Body(..., example="123")
MODEL_PARAMS_BODY = Body(
    ...,
    example={
        "build_year": 2005,
        "building_type_int": 2,
        "latitude": 55.751244,
        "longitude": 37.618423,
        "ceiling_height": 2.7,
        "flats_count": 120,
        "floors_total": 16,
        "has_elevator": 1,
        "floor": 8,
        "kitchen_area": 10.5,
        "living_area": 30.0,
        "rooms": 2,
        "is_apartment": 0,
        "studio": 0,
        "total_area": 54.3,
    },
)


@app.get("/health")
def health_check() -> dict[str, str]:
    """Return service health."""
    return {"status": "ok"}


@app.post("/api/price/")
def get_price_prediction(
    user_id: str = USER_ID_BODY,
    model_params: dict = MODEL_PARAMS_BODY,
) -> dict:
    """Return a real estate price prediction."""
    start = time.perf_counter()
    status_label = "ok"
    try:
        response = app.handler.handle({"user_id": user_id, "model_params": model_params})
        if isinstance(response, dict) and "error" in response:
            status_label = "error"
        return response
    except Exception:
        status_label = "error"
        raise
    finally:
        REQUEST_COUNTER.labels(status=status_label).inc()
        LATENCY_HIST.observe(time.perf_counter() - start)
