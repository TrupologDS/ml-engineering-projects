"""Model loading utilities for the real estate price API."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib


def load_price_model(model_path: str) -> Any:
    """Load a trained price model from a local pickle file."""
    path = Path(model_path)
    if not path.exists():
        raise FileNotFoundError(f"Model file not found: {path}")
    return joblib.load(path)
