"""Recommendation service that blends offline and online candidates."""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

import pandas as pd
import requests
from fastapi import FastAPI

logger = logging.getLogger("uvicorn.error")

FEATURES_URL = os.getenv("FEATURES_URL", "http://127.0.0.1:8010")
EVENTS_URL = os.getenv("EVENTS_URL", "http://127.0.0.1:8020")
PERSONAL_PATH = os.getenv("PERSONAL_PATH", "recsys/recommendations/recommendations.parquet")
TOP_PATH = os.getenv("TOP_PATH", "recsys/recommendations/top_popular.parquet")
LAST_EVENTS_TO_USE = int(os.getenv("LAST_EVENTS_TO_USE", "3"))
FILTER_SEEN = os.getenv("FILTER_SEEN", "1") == "1"


class RecStore:
    """Store offline recommendations and a top-popular fallback."""

    def __init__(self) -> None:
        self.personal: pd.DataFrame | None = None
        self.top: list[int] = []
        self.personal_users: set[int] = set()

    def load(self) -> None:
        df = pd.read_parquet(PERSONAL_PATH)
        order_cols = [c for c in ["user_id", "item_id", "cb_score", "rank"] if c in df.columns]
        df = df[order_cols]
        if "rank" in df.columns:
            df = df.sort_values(["user_id", "rank"])
        elif "cb_score" in df.columns:
            df = df.sort_values(["user_id", "cb_score"], ascending=[True, False])
        self.personal = df
        self.personal_users = set(df["user_id"].unique())
        top = pd.read_parquet(TOP_PATH)[["item_id", "rank"]].sort_values("rank")
        self.top = top["item_id"].tolist()
        logger.info("Offline recommendations loaded")

    def get_offline(self, user_id: int, k: int) -> list[int]:
        if self.personal is not None and user_id in self.personal_users:
            sub = self.personal.loc[self.personal["user_id"] == user_id, "item_id"]
            return sub.head(k).tolist()
        return self.top[:k]


rec_store = RecStore()


def dedup(ids: list[int]) -> list[int]:
    seen: set[int] = set()
    out: list[int] = []
    for item_id in ids:
        if item_id not in seen:
            seen.add(item_id)
            out.append(item_id)
    return out


def get_seen_from_events(user_id: int, k: int = 50) -> list[int]:
    try:
        response = requests.post(
            f"{EVENTS_URL}/get", params={"user_id": user_id, "k": k}, timeout=2.0
        )
        return list(response.json().get("events", []))
    except Exception:
        return []


def online_from_recent(user_id: int, k: int) -> list[int]:
    recent = get_seen_from_events(user_id, LAST_EVENTS_TO_USE)
    items: list[int] = []
    scores: list[float] = []
    for item_id in recent:
        try:
            response = requests.post(
                f"{FEATURES_URL}/similar_items",
                params={"item_id": item_id, "k": k},
                timeout=2.0,
            )
            body = response.json()
            items += body.get("item_id_2", [])
            scores += body.get("score", [])
        except Exception:
            continue
    ranked = sorted(zip(items, scores, strict=False), key=lambda x: x[1], reverse=True)
    return dedup([item_id for item_id, _ in ranked])[:k]


def blend(
    online_list: list[int], offline_list: list[int], top_list: list[int], k: int
) -> list[int]:
    result: list[int] = []
    i = j = 0
    while len(result) < k and (i < len(online_list) or j < len(offline_list)):
        if i < len(online_list):
            result.append(online_list[i])
            i += 1
        if len(result) >= k:
            break
        if j < len(offline_list):
            result.append(offline_list[j])
            j += 1
    result += online_list[i:] + offline_list[j:]
    if len(result) < k:
        result += [item_id for item_id in top_list if item_id not in set(result)]
    return dedup(result)[:k]


@asynccontextmanager
async def lifespan(app: FastAPI):
    rec_store.load()
    logger.info("Recommendations service ready")
    yield


app = FastAPI(title="recommendations", lifespan=lifespan)


@app.post("/recommendations_offline")
async def recommendations_offline(user_id: int, k: int = 100) -> dict[str, list[int]]:
    return {"recs": rec_store.get_offline(user_id, k)}


@app.post("/recommendations_online")
async def recommendations_online(user_id: int, k: int = 100) -> dict[str, list[int]]:
    online = online_from_recent(user_id, k)
    if FILTER_SEEN and online:
        seen = set(get_seen_from_events(user_id, 100))
        online = [item_id for item_id in online if item_id not in seen]
    return {"recs": online[:k]}


@app.post("/recommendations")
async def recommendations(user_id: int, k: int = 100) -> dict[str, list[int]]:
    offline = rec_store.get_offline(user_id, k * 2)
    online = online_from_recent(user_id, k * 2)
    if FILTER_SEEN:
        seen = set(get_seen_from_events(user_id, 100))
        offline = [item_id for item_id in offline if item_id not in seen]
        online = [item_id for item_id in online if item_id not in seen]
    return {"recs": blend(online, offline, rec_store.top, k)}
