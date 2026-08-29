"""Pydantic schemas for ML predictions and evidence documents.

All confidence/score fields are validated to be in [0, 1].
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


# ── ML Prediction Schemas ──────────────────────────────────────────────────────

class ExceptionPredictionSchema(BaseModel):
    """Output of the exception classifier."""
    id: str
    predicted_type: str
    confidence: float = Field(ge=0.0, le=1.0)
    model_version: str
    top_alternatives: list[dict[str, Any]] = []
    created_at: datetime

    model_config = {"from_attributes": True}


class AnomalyPredictionSchema(BaseModel):
    """Output of the anomaly detector."""
    id: str
    is_anomaly: bool
    anomaly_score: float = Field(ge=0.0, le=1.0)
    model_version: str
    created_at: datetime

    model_config = {"from_attributes": True}


class MLAnalysisResponse(BaseModel):
    """Combined ML analysis response returned by /run-ml."""
    exception_id: str
    classifier: Optional[ExceptionPredictionSchema] = None
    anomaly: Optional[AnomalyPredictionSchema] = None
    models_available: bool
    message: str


# ── Evidence Schemas ───────────────────────────────────────────────────────────

class EvidenceDocumentResponse(BaseModel):
    """A single evidence document (without the raw embedding vector)."""
    id: str
    merchant_id: Optional[str] = None
    source_type: str
    source_id: Optional[str] = None
    title: str
    content: str
    metadata: Optional[dict[str, Any]] = None
    trust_level: str
    similarity_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    created_at: Optional[str] = None


class EvidenceSearchRequest(BaseModel):
    """Request body for POST /evidence/search."""
    query: str = Field(min_length=1, max_length=1000)
    top_k: int = Field(default=7, ge=1, le=20)
    source_types: Optional[list[str]] = None


class EvidenceSearchResponse(BaseModel):
    """Response from POST /evidence/search."""
    query: str
    results: list[EvidenceDocumentResponse]
    total: int


class EvidenceCountsSchema(BaseModel):
    transactions: int = 0
    settlements: int = 0
    invoices: int = 0
    bank_transactions: int = 0
    finance_rules: int = 0
    historical_cases: int = 0
    total: int = 0


class EvidenceBundleResponse(BaseModel):
    """Evidence bundle for an exception (from /exceptions/{id}/evidence)."""
    exception_id: str
    transaction_evidence: list[EvidenceDocumentResponse] = []
    settlement_evidence: list[EvidenceDocumentResponse] = []
    invoice_evidence: list[EvidenceDocumentResponse] = []
    bank_evidence: list[EvidenceDocumentResponse] = []
    finance_rules: list[EvidenceDocumentResponse] = []
    historical_cases: list[EvidenceDocumentResponse] = []
    counts: EvidenceCountsSchema


class MLAgreementSchema(BaseModel):
    deterministic_type: str
    ml_type: str
    agree: bool
    note: str


class IntelligenceContextResponse(BaseModel):
    """Full intelligence context for Phase 3B agent consumption.

    This is the primary output of GET /exceptions/{id}/intelligence-context.
    Phase 3B will feed this directly into the LangGraph investigator.
    """
    exception_id: str
    deterministic_analysis: dict[str, Any]
    ml_prediction: Optional[dict[str, Any]] = None
    anomaly_analysis: Optional[dict[str, Any]] = None
    ml_agreement: Optional[MLAgreementSchema] = None
    models_available: bool
    evidence: list[EvidenceDocumentResponse] = []
    evidence_counts: EvidenceCountsSchema
    transaction_evidence: list[EvidenceDocumentResponse] = []
    settlement_evidence: list[EvidenceDocumentResponse] = []
    invoice_evidence: list[EvidenceDocumentResponse] = []
    bank_evidence: list[EvidenceDocumentResponse] = []
    finance_rules: list[EvidenceDocumentResponse] = []
    historical_cases: list[EvidenceDocumentResponse] = []
    phase_3b_ready: bool = False
