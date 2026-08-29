"""ML prediction model — stores ML classifier and anomaly detection results.

A prediction is immutable once written.
New predictions create new rows; they never overwrite old ones.
This preserves the history of ML analysis over time.
"""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, Float, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ModelType(str, enum.Enum):
    EXCEPTION_CLASSIFIER = "EXCEPTION_CLASSIFIER"
    ANOMALY_DETECTOR = "ANOMALY_DETECTOR"


class MLPrediction(Base):
    __tablename__ = "ml_predictions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # Which merchant's data this prediction belongs to
    merchant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    # The entity being predicted on (e.g. "exception", "transaction")
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    entity_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)

    model_type: Mapped[ModelType] = mapped_column(
        Enum(ModelType), nullable=False, index=True
    )
    model_version: Mapped[str] = mapped_column(String(64), nullable=False)

    # Primary prediction output (class label or "anomaly"/"normal")
    prediction: Mapped[str] = mapped_column(String(128), nullable=False)
    # Confidence or anomaly score in [0, 1]
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Raw anomaly score from IsolationForest (higher = more anomalous, in [0,1])
    score: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Snapshot of features used for this prediction (JSONB for auditability)
    features_snapshot: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # Top alternative predictions [{"label": str, "confidence": float}, ...]
    top_alternatives: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    __table_args__ = (
        Index("ix_ml_predictions_entity", "entity_type", "entity_id"),
        Index("ix_ml_predictions_merchant_model", "merchant_id", "model_type"),
    )

    def __repr__(self) -> str:
        return f"<MLPrediction {self.model_type} {self.entity_id} → {self.prediction}>"
