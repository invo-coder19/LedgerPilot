"""Evidence service — orchestrates ML + RAG for intelligence context.

Builds the complete IntelligenceContext response used by:
  - GET /api/v1/exceptions/{id}/intelligence-context
  - GET /api/v1/exceptions/{id}/evidence

This is the primary integration point between:
  - Phase 1 (exception/transaction data)
  - Phase 3A ML layer (predictions)
  - Phase 3A RAG layer (evidence retrieval)
"""

from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy.orm import Session

from app.ml.inference import models_ready
from app.models.exception import Exception as FinancialException
from app.models.ml_prediction import ModelType
from app.rag.retriever import EvidenceRetriever
from app.repositories.evidence_document_repository import EvidenceDocumentRepository
from app.repositories.ml_prediction_repository import MLPredictionRepository


class EvidenceService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.retriever = EvidenceRetriever(db)
        self.ml_repo = MLPredictionRepository(db)
        self.evidence_repo = EvidenceDocumentRepository(db)

    def get_intelligence_context(
        self,
        exception: FinancialException,
        merchant_id: uuid.UUID,
    ) -> dict:
        """Assemble the full intelligence context for an exception.

        Returns a structured dict ready to be serialised as IntelligenceContext.
        This is the payload Phase 3B will consume.
        """
        exc_id = str(exception.id)

        # ── ML predictions ─────────────────────────────────────────────────────
        classifier_pred = self.ml_repo.get_latest_for_entity(
            "exception", exc_id, ModelType.EXCEPTION_CLASSIFIER
        )
        anomaly_pred = self.ml_repo.get_latest_for_entity(
            "exception", exc_id, ModelType.ANOMALY_DETECTOR
        )

        ml_prediction = None
        if classifier_pred:
            ml_prediction = {
                "id": str(classifier_pred.id),
                "predicted_type": classifier_pred.prediction,
                "confidence": classifier_pred.confidence,
                "model_version": classifier_pred.model_version,
                "top_alternatives": classifier_pred.top_alternatives or [],
                "created_at": classifier_pred.created_at.isoformat(),
            }

        anomaly_analysis = None
        if anomaly_pred:
            anomaly_analysis = {
                "id": str(anomaly_pred.id),
                "is_anomaly": anomaly_pred.prediction == "ANOMALY",
                "anomaly_score": anomaly_pred.score,
                "model_version": anomaly_pred.model_version,
                "created_at": anomaly_pred.created_at.isoformat(),
            }

        # ── Evidence bundle ────────────────────────────────────────────────────
        evidence_bundle = self.retriever.build_exception_evidence_bundle(
            exception_id=exc_id,
            source_id=exception.source_id,
            merchant_id=merchant_id,
            description=exception.description,
        )

        # ── Deterministic analysis (Phase 1 data) ──────────────────────────────
        deterministic_analysis = {
            "exception_type": str(exception.exception_type),
            "severity": str(exception.severity),
            "source_type": exception.source_type,
            "source_id": exception.source_id,
            "description": exception.description,
            "status": str(exception.status),
        }

        # Agreement check between deterministic and ML results
        ml_agreement = None
        if ml_prediction:
            det_type = str(exception.exception_type)
            ml_type = ml_prediction["predicted_type"]
            ml_agreement = {
                "deterministic_type": det_type,
                "ml_type": ml_type,
                "agree": det_type == ml_type or (
                    det_type in ("AMOUNT_MISMATCH", "FEE_VARIANCE")
                    and ml_type in ("AMOUNT_MISMATCH", "FEE_VARIANCE")
                ),
                "note": (
                    "Deterministic and ML classifications agree."
                    if det_type == ml_type else
                    f"Deterministic: {det_type} | ML: {ml_type}. "
                    "Both preserved — investigate discrepancy."
                ),
            }

        return {
            "exception_id": exc_id,
            "deterministic_analysis": deterministic_analysis,
            "ml_prediction": ml_prediction,
            "anomaly_analysis": anomaly_analysis,
            "ml_agreement": ml_agreement,
            "models_available": models_ready(),
            "evidence": evidence_bundle["all_evidence"],
            "evidence_counts": evidence_bundle["counts"],
            "transaction_evidence": evidence_bundle["transaction_evidence"],
            "settlement_evidence": evidence_bundle["settlement_evidence"],
            "invoice_evidence": evidence_bundle["invoice_evidence"],
            "bank_evidence": evidence_bundle["bank_evidence"],
            "finance_rules": evidence_bundle["finance_rules"],
            "historical_cases": evidence_bundle["historical_cases"],
            "phase_3b_ready": (
                ml_prediction is not None and anomaly_analysis is not None
            ),
        }

    def search_evidence(
        self,
        query: str,
        merchant_id: Optional[uuid.UUID],
        top_k: int = 7,
        source_types: Optional[list[str]] = None,
    ) -> list[dict]:
        """Semantic + hybrid evidence search."""
        return self.retriever.search(
            query=query,
            merchant_id=merchant_id,
            top_k=top_k,
            source_types=source_types,
        )

    def get_evidence_document(self, doc_id: uuid.UUID) -> Optional[dict]:
        doc = self.evidence_repo.get_by_id(doc_id)
        if doc is None:
            return None
        return {
            "id": str(doc.id),
            "merchant_id": str(doc.merchant_id) if doc.merchant_id else None,
            "source_type": str(doc.source_type),
            "source_id": doc.source_id,
            "title": doc.title,
            "content": doc.content,
            "metadata": doc.metadata_,
            "trust_level": str(doc.trust_level),
            "created_at": doc.created_at.isoformat(),
        }
