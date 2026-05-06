"""Request validation and prediction logic for the real estate price API."""

from __future__ import annotations

import logging
import os
from typing import Any

import pandas as pd

from services.ml_service.model_loader import load_price_model

logger = logging.getLogger("ml_service")


class FastApiHandler:
    """Validate API payloads and call the loaded model."""

    def __init__(self) -> None:
        self.param_types = {"user_id": (str, int), "model_params": dict}
        self.model_path = os.getenv("MODEL_PATH", "services/models/model.pkl")
        try:
            self.model = load_price_model(self.model_path)
            logger.info("Model loaded successfully")
        except Exception:
            logger.exception("Model loading failed")
            self.model = None

        if self.model is not None and hasattr(self.model, "feature_names_in_"):
            self.required_model_params = list(self.model.feature_names_in_)
        else:
            # Keep request validation available even when the private model artifact is absent.
            self.required_model_params = [
                "build_year",
                "building_type_int",
                "latitude",
                "longitude",
                "ceiling_height",
                "flats_count",
                "floors_total",
                "has_elevator",
                "floor",
                "kitchen_area",
                "living_area",
                "rooms",
                "is_apartment",
                "studio",
                "total_area",
            ]

    def check_required_query_params(self, query_params: dict[str, Any]) -> bool:
        """Check top-level payload keys and value types."""
        if "user_id" not in query_params or "model_params" not in query_params:
            return False
        if not isinstance(query_params["user_id"], self.param_types["user_id"]):
            return False
        return isinstance(query_params["model_params"], self.param_types["model_params"])

    def diff_required_model_params(
        self, model_params: dict[str, Any]
    ) -> tuple[list[str], list[str]]:
        """Return missing and extra feature names."""
        given = set(model_params.keys())
        required = set(self.required_model_params)
        return sorted(required - given), sorted(given - required)

    def check_required_model_params(self, model_params: dict[str, Any]) -> bool:
        """Return True when payload features match the model schema."""
        missing, extra = self.diff_required_model_params(model_params)
        return not missing and not extra

    def validate_params(self, params: dict[str, Any]) -> bool:
        """Validate the full API request payload."""
        return self.check_required_query_params(params) and self.check_required_model_params(
            params["model_params"]
        )

    def predict_price(self, model_params: dict[str, Any]) -> float:
        """Predict price for one feature row."""
        if self.model is None:
            raise RuntimeError("Model is not loaded")
        x = pd.DataFrame([model_params], columns=self.required_model_params)
        return float(self.model.predict(x)[0])

    def handle(self, params: dict[str, Any]) -> dict[str, Any]:
        """Process an API request and return either prediction or validation details."""
        try:
            if not self.validate_params(params):
                missing, extra = self.diff_required_model_params(params.get("model_params", {}))
                return {
                    "error": "invalid_parameters",
                    "details": {"missing_features": missing, "extra_features": extra},
                }
            return {
                "user_id": params["user_id"],
                "prediction": self.predict_price(params["model_params"]),
            }
        except Exception as exc:
            logger.exception("Request handling failed")
            return {"error": "request_failed", "details": str(exc)}
