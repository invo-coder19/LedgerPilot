"""ML inference service.

Provides run_classifier() and run_anomaly_detector() that:
  1. Build feature vectors from live ORM records
  2. Run model predictions
  3. Persist predictions to ml_predictions table
  4. Return Pydantic response schemas

Models are loaded once and cached in module-level variables.
If models are not trained yet, the endpoint returns a graceful 503.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.ml import model_registry
from app.ml.anomaly_detection import AnomalyDetector
from app.ml.exception_classifier import ExceptionClassifier
from app.ml.features import extract_features, features_to_array
from app.models.ml_prediction import MLPrediction, ModelType
from app.schemas.ml import AnomalyPredictionSchema, ExceptionPredictionSchema

# ── Module-level model cache (lazy loaded) ────────────────────────────────────

_classifier: Optional[ExceptionClassifier] = None
_detector: Optional[AnomalyDetector] = None


def _get_classifier() -> ExceptionClassifier:
    global _classifier
    if _classifier is None:
        _classifier = model_registry.load_classifier()
    return _classifier


def _get_detector() -> AnomalyDetector:
    global _detector
    if _detector is None:
        _detector = model_registry.load_anomaly_detector()
    return _detector


def invalidate_cache() -> None:
    """Force model reload on next inference (e.g. after retraining)."""
    global _classifier, _detector
    _classifier = None
    _detector = None


# ── Record → feature dict builders ───────────────────────────────────────────

def _exception_to_record(exception_row: object, related: dict) -> dict:
    """Build a feature record dict from a financial exception + related data."""
    return {
        "amount": getattr(exception_row, "amount", None),
        "fee": related.get("fee"),
        "tax": related.get("tax"),
        "settlement_amount": related.get("settlement_amount"),
        "transaction_date": related.get("transaction_date"),
        "settlement_date": related.get("settlement_date"),
        "status": related.get("status", "UNKNOWN"),
        "payment_method": related.get("payment_method"),
        "has_invoice": related.get("has_invoice", False),
        "has_settlement": related.get("has_settlement", False),
        "has_bank_credit": related.get("has_bank_credit", False),
    }


# ── Public inference API ──────────────────────────────────────────────────────

def run_classifier(
    db: Session,
    exception_row: object,
    related: dict,
    merchant_id: uuid.UUID | None = None,
) -> ExceptionPredictionSchema:
    """Run the exception classifier for a given exception record.

    Parameters
    ----------
    db           : Active SQLAlchemy session for persisting the result.
    exception_row: Exception ORM row (used for entity_id, amount).
    related      : Dict with keys: fee, tax, settlement_amount,
                   transaction_date, settlement_date, status,
                   payment_method, has_invoice, has_settlement, has_bank_credit.
    merchant_id  : Merchant UUID for scoping (for audit trail).

    Returns
    -------
    ExceptionPredictionSchema
    """
    clf = _get_classifier()
    record = _exception_to_record(exception_row, related)
    features = extract_features(record)
    x = features_to_array(features)
    result = clf.predict_single(x)

    prediction = MLPrediction(
        merchant_id=merchant_id,
        entity_type="exception",
        entity_id=str(exception_row.id),
        model_type=ModelType.EXCEPTION_CLASSIFIER,
        model_version=ExceptionClassifier.MODEL_VERSION,
        prediction=result["predicted_type"],
        confidence=result["confidence"],
        score=result["confidence"],
        features_snapshot={k: round(v, 6) for k, v in features.items()},
        top_alternatives=result["top_alternatives"],
    )
    db.add(prediction)
    db.commit()
    db.refresh(prediction)

    return ExceptionPredictionSchema(
        id=str(prediction.id),
        predicted_type=result["predicted_type"],
        confidence=result["confidence"],
        model_version=ExceptionClassifier.MODEL_VERSION,
        top_alternatives=result["top_alternatives"],
        created_at=prediction.created_at,
    )


def run_anomaly_detector(
    db: Session,
    exception_row: object,
    related: dict,
    merchant_id: uuid.UUID | None = None,
) -> AnomalyPredictionSchema:
    """Run anomaly detection for a given exception record."""
    det = _get_detector()
    record = _exception_to_record(exception_row, related)
    features = extract_features(record)
    x = features_to_array(features)
    result = det.predict_single(x)

    prediction = MLPrediction(
        merchant_id=merchant_id,
        entity_type="exception",
        entity_id=str(exception_row.id),
        model_type=ModelType.ANOMALY_DETECTOR,
        model_version=AnomalyDetector.MODEL_VERSION,
        prediction="ANOMALY" if result["is_anomaly"] else "NORMAL",
        confidence=result["anomaly_score"],
        score=result["anomaly_score"],
        features_snapshot={k: round(v, 6) for k, v in features.items()},
    )
    db.add(prediction)
    db.commit()
    db.refresh(prediction)

    return AnomalyPredictionSchema(
        id=str(prediction.id),
        is_anomaly=result["is_anomaly"],
        anomaly_score=result["anomaly_score"],
        model_version=AnomalyDetector.MODEL_VERSION,
        created_at=prediction.created_at,
    )


def models_ready() -> bool:
    """Return True if both model artifacts exist on disk."""
    return model_registry.models_exist()
