"""In-memory online event store for recent user interactions."""

from __future__ import annotations

from fastapi import FastAPI


class EventStore:
    """Keep the latest item interactions per user."""

    def __init__(self, max_events_per_user: int = 10) -> None:
        self.events: dict[int, list[int]] = {}
        self.max_events_per_user = max_events_per_user

    def put(self, user_id: int, item_id: int) -> None:
        history = self.events.get(user_id, [])
        self.events[user_id] = [item_id] + history[: self.max_events_per_user]

    def get(self, user_id: int, k: int) -> list[int]:
        return self.events.get(user_id, [])[:k]


events_store = EventStore()
app = FastAPI(title="events")


@app.post("/put")
async def put(user_id: int, item_id: int) -> dict[str, str]:
    events_store.put(user_id, item_id)
    return {"result": "ok"}


@app.post("/get")
async def get(user_id: int, k: int = 10) -> dict[str, list[int]]:
    return {"events": events_store.get(user_id, k)}
