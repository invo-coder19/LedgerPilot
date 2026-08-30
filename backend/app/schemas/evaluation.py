"""Phase 5 — Evaluation API schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel

from app.schemas.common import ORMBase


class EvaluationDatasetResponse(ORMBase):
    id: str
    name: str
    version: str
    description: Optional[str] = None
    record_count: int
    random_seed: Optional[int] = None
    distribution: Optional[dict[str, Any]] = None
    is_active: bool
    created_at: datetime


class EvaluationRunCreate(BaseModel):
    dataset_name: str
    version: str = "v1"


class EvaluationRunResponse(ORMBase):
    id: str
    dataset_id: str
    version: str
    status: str
    records_tested: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    configuration: Optional[dict[str, Any]] = None
    error_message: Optional[str] = None
    created_at: datetime


class EvaluationResultResponse(BaseModel):
    metric_name: str
    metric_value: float
    category: Optional[str] = None
    metric_metadata: Optional[dict[str, Any]] = None


class EvaluationRunDetailResponse(EvaluationRunResponse):
    metrics: dict[str, dict[str, Any]] = {}


class EvaluationSummaryResponse(BaseModel):
    """Competition-ready summary for the evaluation dashboard."""
    # Run metadata
    run_id: Optional[str] = None
    records_tested: int = 0
    dataset_version: Optional[str] = None
    status: str = "NO_DATA"

    # Reconciliation
    reconciliation_accuracy: float = 0.0
    match_rate: float = 0.0
    reconciliation_precision: float = 0.0
    reconciliation_recall: float = 0.0
    false_positive_rate: float = 0.0

    # ML
    ml_accuracy: float = 0.0
    ml_f1_macro: float = 0.0
    ml_f1_weighted: float = 0.0

    # AI Investigator
    citation_correctness: float = 0.0
    uncertainty_accuracy: float = 0.0

    # Controller
    auto_resolution_precision: float = 0.0
    auto_resolution_rate: float = 0.0
    human_review_rate: float = 0.0
    escalation_rate: float = 0.0
    decision_accuracy: float = 0.0

    # Financial
    false_positive_cost_inr: float = 0.0
    false_negative_cost_inr: float = 0.0
    autonomous_error_rate: float = 0.0
    financial_error_rate: float = 0.0
    amount_processed_inr: float = 0.0
    amount_auto_resolved_inr: float = 0.0
    human_interventions_avoided: int = 0


class EvaluationCompareResponse(BaseModel):
    run_a: EvaluationRunDetailResponse
    run_b: EvaluationRunDetailResponse
    diff: dict[str, dict[str, Any]] = {}


class GenerateDatasetRequest(BaseModel):
    records: int = 1000
    seed: int = 42
    name: str = "benchmark_v1"
    version: str = "v1"
    distribution: Optional[dict[str, float]] = None
