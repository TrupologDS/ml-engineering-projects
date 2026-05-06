"""Item-to-item similarity service for online recommendations."""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

import pandas as pd
from fastapi import FastAPI

logger = logging.getLogger("uvicorn.error")
SIMILAR_PATH = os.getenv("SIMILAR_PATH", "recsys/recommendations/similar.parquet")


class SimilarItems:
    """Serve top similar items from a parquet artifact."""

    def __init__(self) -> None:
        self.df: pd.DataFrame | None = None

    def load(self, path: str) -> None:
        df = pd.read_parquet(path, columns=["item_id_1", "item_id_2", "score"])
        self.df = df.set_index("item_id_1")
        logger.info("Similar items loaded")

    def get(self, item_id: int, k: int = 10) -> dict[str, list]:
        if self.df is None:
            return {"item_id_2": [], "score": []}
        try:
            sub = self.df.loc[item_id].head(k)
            return {"item_id_2": sub["item_id_2"].tolist(), "score": sub["score"].tolist()}
        except KeyError:
            return {"item_id_2": [], "score": []}


sim_store = SimilarItems()


@asynccontextmanager
async def lifespan(app: FastAPI):
    sim_store.load(SIMILAR_PATH)
    logger.info("Features service ready")
    yield


app = FastAPI(title="features", lifespan=lifespan)


@app.post("/similar_items")
async def similar_items(item_id: int, k: int = 10) -> dict[str, list]:
    return sim_store.get(item_id, k)
