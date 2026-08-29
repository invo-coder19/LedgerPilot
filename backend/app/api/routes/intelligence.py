"""Intelligence API routes — Phase 3A.

All routes require authentication.
Merchant isolation is enforced on every query.

In Phase 1 the User model has no merchant_id field (single-tenant deployment).
We resolve the merchant by fetching the first merchant associated with the DB.
In a multi-tenant Phase 4 deployment, the user-to-merchant relationship
should be established in the User model.

Routes:
  POST  /exceptions/{id}/run-ml               — trigger ML inference
  GET   /exceptions/{id}/intelligence-context  — full context for Phase 3B
  GET   /exceptions/{id}/evidence              — evidence bundle
  POST  /evidence/search                       — semantic search
  GET   /evidence/{id}                         — single evidence document
"""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser
from app.core.database import get_db
from app.ml import inference as ml_inference
from app.models.audit_log import AuditAction
from app.models.exception import Exception as FinancialException
from app.models.merchant import Merchant
from app.models.ml_prediction import ModelType
from app.rag.evidence_service import EvidenceService
from app.repositories.ml_prediction_repository import MLPredictionRepository
from app.schemas.ml import (
    EvidenceBundleResponse,
    EvidenceCountsSchema,
    EvidenceDocumentResponse,
    EvidenceSearchRequest,
    EvidenceSearchResponse,
    IntelligenceContextResponse,
    MLAnalysisResponse,
)
from app.services.audit_service import AuditService

router = APIRouter(prefix="/intelligence", tags=["Intelligence"])


# ── Helpers ───────────────────────────────────────────────────────────────────

def _resolve_merchant_id(db: Session) -> Optional[uuid.UUID]:
    """Resolve the active merchant ID.

    Phase 1 is single-tenant — returns the first merchant in the DB.
    Phase 4 will look up merchant_id from the User record.
    """
    merchant = db.query(Merchant).first()
    return merchant.id if merchant else None


def _get_exception_or_404(
    exception_id: str,
    db: Session,
    merchant_id: Optional[uuid.UUID],
) -> FinancialException:
    """Load an exception, enforcing merchant isolation where applicable."""
    try:
        exc_uuid = uuid.UUID(exception_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid exception ID format.")

    exc = db.get(FinancialException, exc_uuid)
    if exc is None:
        raise HTTPException(status_code=404, detail="Exception not found.")
    # Enforce merchant isolation when merchant_id is known
    if merchant_id is not None and exc.merchant_id != merchant_id:
        raise HTTPException(status_code=403, detail="Access denied.")
    return exc




def _evidence_doc_response(raw: dict) -> EvidenceDocumentResponse:
    """Convert a raw evidence search result dict to response schema."""
    score = raw.get("similarity_score")
    if score is not None:
        score = round(float(score), 4)
    return EvidenceDocumentResponse(
        id=str(raw["id"]),
        merchant_id=str(raw.get("merchant_id")) if raw.get("merchant_id") else None,
        source_type=str(raw["source_type"]),
        source_id=raw.get("source_id"),
        title=raw["title"],
        content=raw["content"],
        metadata=raw.get("metadata") or raw.get("metadata_"),
        trust_level=str(raw["trust_level"]),
        similarity_score=score,
        created_at=raw.get("created_at"),
    )


def _build_evidence_bundle_response(
    exception_id: str, bundle: dict
) -> EvidenceBundleResponse:
    counts = bundle.get("counts", {})
    return EvidenceBundleResponse(
        exception_id=exception_id,
        transaction_evidence=[_evidence_doc_response(r) for r in bundle.get("transaction_evidence", [])],
        settlement_evidence=[_evidence_doc_response(r) for r in bundle.get("settlement_evidence", [])],
        invoice_evidence=[_evidence_doc_response(r) for r in bundle.get("invoice_evidence", [])],
        bank_evidence=[_evidence_doc_response(r) for r in bundle.get("bank_evidence", [])],
        finance_rules=[_evidence_doc_response(r) for r in bundle.get("finance_rules", [])],
        historical_cases=[_evidence_doc_response(r) for r in bundle.get("historical_cases", [])],
        counts=EvidenceCountsSchema(
            transactions=counts.get("transactions", 0),
            settlements=counts.get("settlements", 0),
            invoices=counts.get("invoices", 0),
            bank_transactions=counts.get("bank_transactions", 0),
            finance_rules=counts.get("finance_rules", 0),
            historical_cases=counts.get("historical_cases", 0),
            total=counts.get("total", 0),
        ),
    )


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/exceptions/{exception_id}/run-ml", response_model=MLAnalysisResponse)
def run_ml_analysis(
    exception_id: str,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
) -> MLAnalysisResponse:
    """Trigger ML inference (classifier + anomaly detector) for an exception.

    Persists predictions and returns the results.
    If models are not trained, returns a 503.
    """
    merchant_id = _resolve_merchant_id(db)
    exc = _get_exception_or_404(exception_id, db, merchant_id)

    audit = AuditService(db)
    audit.log(
        AuditAction.ML_ANALYSIS_REQUESTED,
        f"ML analysis requested for exception {exception_id}",
        user_id=current_user.id,
        merchant_id=merchant_id,
        entity_type="exception",
        entity_id=exception_id,
    )

    if not ml_inference.models_ready():
        return MLAnalysisResponse(
            exception_id=exception_id,
            classifier=None,
            anomaly=None,
            models_available=False,
            message=(
                "ML models are not trained yet. "
                "Run `python -m app.ml.training` to train them."
            ),
        )

    # Build feature context from related data (simplified — uses exception amount)
    related = {
        "fee": None,
        "tax": None,
        "settlement_amount": float(exc.amount) if exc.amount else None,
        "transaction_date": None,
        "settlement_date": None,
        "status": exc.exception_type.value,
        "payment_method": None,
        "has_invoice": exc.exception_type.value not in ("MISSING_INVOICE",),
        "has_settlement": exc.exception_type.value not in ("MISSING_SETTLEMENT",),
        "has_bank_credit": True,
    }

    classifier_result = ml_inference.run_classifier(db, exc, related, merchant_id)
    anomaly_result = ml_inference.run_anomaly_detector(db, exc, related, merchant_id)

    audit.log(
        AuditAction.ML_ANALYSIS_COMPLETED,
        f"ML analysis completed: {classifier_result.predicted_type} "
        f"(conf={classifier_result.confidence:.2f}), "
        f"anomaly={anomaly_result.is_anomaly}",
        user_id=current_user.id,
        merchant_id=merchant_id,
        entity_type="exception",
        entity_id=exception_id,
    )

    return MLAnalysisResponse(
        exception_id=exception_id,
        classifier=classifier_result,
        anomaly=anomaly_result,
        models_available=True,
        message="ML analysis complete.",
    )


@router.get(
    "/exceptions/{exception_id}/intelligence-context",
    response_model=IntelligenceContextResponse,
)
def get_intelligence_context(
    exception_id: str,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
) -> IntelligenceContextResponse:
    """Full intelligence context for an exception — designed for Phase 3B.

    Returns:
      - Deterministic analysis (exception data)
      - ML classification result (if models trained)
      - Anomaly detection result (if models trained)
      - Agreement check between deterministic and ML results
      - Full evidence bundle (related records + rules + historical cases)
    """
    merchant_id = _resolve_merchant_id(db)
    exc = _get_exception_or_404(exception_id, db, merchant_id)

    svc = EvidenceService(db)
    ctx = svc.get_intelligence_context(exc, merchant_id)

    AuditService(db).log(
        AuditAction.INTELLIGENCE_CONTEXT_VIEWED,
        f"Intelligence context viewed for exception {exception_id}",
        user_id=current_user.id,
        merchant_id=merchant_id,
        entity_type="exception",
        entity_id=exception_id,
    )

    counts = ctx.get("evidence_counts", {})
    return IntelligenceContextResponse(
        exception_id=exception_id,
        deterministic_analysis=ctx["deterministic_analysis"],
        ml_prediction=ctx["ml_prediction"],
        anomaly_analysis=ctx["anomaly_analysis"],
        ml_agreement=ctx.get("ml_agreement"),
        models_available=ctx["models_available"],
        evidence=[_evidence_doc_response(r) for r in ctx.get("evidence", [])],
        evidence_counts=EvidenceCountsSchema(
            transactions=counts.get("transactions", 0),
            settlements=counts.get("settlements", 0),
            invoices=counts.get("invoices", 0),
            bank_transactions=counts.get("bank_transactions", 0),
            finance_rules=counts.get("finance_rules", 0),
            historical_cases=counts.get("historical_cases", 0),
            total=counts.get("total", 0),
        ),
        transaction_evidence=[_evidence_doc_response(r) for r in ctx.get("transaction_evidence", [])],
        settlement_evidence=[_evidence_doc_response(r) for r in ctx.get("settlement_evidence", [])],
        invoice_evidence=[_evidence_doc_response(r) for r in ctx.get("invoice_evidence", [])],
        bank_evidence=[_evidence_doc_response(r) for r in ctx.get("bank_evidence", [])],
        finance_rules=[_evidence_doc_response(r) for r in ctx.get("finance_rules", [])],
        historical_cases=[_evidence_doc_response(r) for r in ctx.get("historical_cases", [])],
        phase_3b_ready=ctx.get("phase_3b_ready", False),
    )


@router.get(
    "/exceptions/{exception_id}/evidence",
    response_model=EvidenceBundleResponse,
)
def get_exception_evidence(
    exception_id: str,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
) -> EvidenceBundleResponse:
    """Evidence bundle for an exception — related records, rules, cases."""
    merchant_id = _resolve_merchant_id(db)
    exc = _get_exception_or_404(exception_id, db, merchant_id)

    svc = EvidenceService(db)
    bundle = svc.retriever.build_exception_evidence_bundle(
        exception_id=exception_id,
        source_id=exc.source_id,
        merchant_id=merchant_id,
        description=exc.description,
    )

    AuditService(db).log(
        AuditAction.EVIDENCE_VIEWED,
        f"Evidence bundle viewed for exception {exception_id}",
        user_id=current_user.id,
        merchant_id=merchant_id,
        entity_type="exception",
        entity_id=exception_id,
    )

    return _build_evidence_bundle_response(exception_id, bundle)


@router.post("/evidence/search", response_model=EvidenceSearchResponse)
def search_evidence(
    request: EvidenceSearchRequest,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
) -> EvidenceSearchResponse:
    """Semantic + hybrid evidence search scoped to the current merchant."""
    merchant_id = _resolve_merchant_id(db)

    svc = EvidenceService(db)
    results = svc.search_evidence(
        query=request.query,
        merchant_id=merchant_id,
        top_k=request.top_k,
        source_types=request.source_types,
    )

    AuditService(db).log(
        AuditAction.EVIDENCE_SEARCHED,
        f"Evidence searched: '{request.query[:80]}'",
        user_id=current_user.id,
        merchant_id=merchant_id,
    )

    return EvidenceSearchResponse(
        query=request.query,
        results=[_evidence_doc_response(r) for r in results],
        total=len(results),
    )


@router.get("/evidence/{evidence_id}", response_model=EvidenceDocumentResponse)
def get_evidence_document(
    evidence_id: str,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
) -> EvidenceDocumentResponse:
    """Retrieve a single evidence document by ID."""
    try:
        doc_uuid = uuid.UUID(evidence_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid evidence ID format.")

    svc = EvidenceService(db)
    doc = svc.get_evidence_document(doc_uuid)
    if doc is None:
        raise HTTPException(status_code=404, detail="Evidence document not found.")

    merchant_id = _resolve_merchant_id(db)
    # Merchant isolation: doc must belong to current merchant or be global
    if doc.get("merchant_id") and merchant_id and doc["merchant_id"] != str(merchant_id):
        raise HTTPException(status_code=403, detail="Access denied.")

    AuditService(db).log(
        AuditAction.EVIDENCE_VIEWED,
        f"Evidence document viewed: {evidence_id}",
        user_id=current_user.id,
        merchant_id=merchant_id,
        entity_type="evidence_document",
        entity_id=evidence_id,
    )

    return EvidenceDocumentResponse(**doc)
