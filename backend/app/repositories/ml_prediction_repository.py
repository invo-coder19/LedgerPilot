"""ML prediction repository — CRUD for ml_predictions table."""

from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy.orm import Session

from app.models.ml_prediction import MLPrediction, ModelType


class MLPredictionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, prediction: MLPrediction) -> MLPrediction:
        self.db.add(prediction)
        self.db.flush()
        return prediction

    def get_latest_for_entity(
        self,
        entity_type: str,
        entity_id: str,
        model_type: ModelType,
    ) -> Optional[MLPrediction]:
        """Return the most recent prediction for a given entity + model type."""
        return (
            self.db.query(MLPrediction)
            .filter(
                MLPrediction.entity_type == entity_type,
                MLPrediction.entity_id == entity_id,
                MLPrediction.model_type == model_type,
            )
            .order_by(MLPrediction.created_at.desc())
            .first()
        )

    def list_for_entity(
        self,
        entity_type: str,
        entity_id: str,
        limit: int = 10,
    ) -> list[MLPrediction]:
        return (
            self.db.query(MLPrediction)
            .filter(
                MLPrediction.entity_type == entity_type,
                MLPrediction.entity_id == entity_id,
            )
            .order_by(MLPrediction.created_at.desc())
            .limit(limit)
            .all()
        )

    def list_for_merchant(
        self,
        merchant_id: uuid.UUID,
        model_type: Optional[ModelType] = None,
        limit: int = 50,
    ) -> list[MLPrediction]:
        q = self.db.query(MLPrediction).filter(
            MLPrediction.merchant_id == merchant_id
        )
        if model_type is not None:
            q = q.filter(MLPrediction.model_type == model_type)
        return q.order_by(MLPrediction.created_at.desc()).limit(limit).all()
