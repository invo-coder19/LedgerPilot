"""Pydantic schemas for AI investigation API."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

ROOT_CAUSES = Literal[
    "FEE_VARIANCE", "AMOUNT_MISMATCH", "DUPLICATE",
    "MISSING_INVOICE", "MISSING_SETTLEMENT", "REFUND_MISMATCH",
    "DATE_MISMATCH", "UNKNOWN",
]


class InvestigationResultSchema(BaseModel):
    """Structured result of an AI investigation."""
    exception_id: str
    root_cause: str
    confidence: float = Field(ge=0.0, le=1.0)
    confidence_band: str               # HIGH / MEDIUM / LOW
    conclusion: str
    observed_facts: list[str] = []
    inferences: list[str] = []
    evidence_ids: list[str] = []
    recommendation: str
    next_steps: list[str] = []
    uncertainties: list[str] = []
    requires_human_review: bool
    contradiction_detected: bool = False


class InvestigationStepResponse(BaseModel):
    id: str
    step_name: str
    tool_name: Optional[str] = None
    input_summary: Optional[str] = None
    output_summary: Optional[str] = None
    duration_ms: Optional[int] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class InvestigationRunResponse(BaseModel):
    id: str
    exception_id: str
    merchant_id: Optional[str] = None
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    model_provider: Optional[str] = None
    model_name: Optional[str] = None
    final_result: Optional[dict[str, Any]] = None
    final_confidence: Optional[float] = None
    confidence_band: Optional[str] = None
    requires_human: bool
    error_message: Optional[str] = None
    duration_ms: Optional[int] = None
    steps: list[InvestigationStepResponse] = []

    model_config = {"from_attributes": True}


class StartInvestigationResponse(BaseModel):
    investigation_id: str
    status: str
    result: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    message: str


class CopilotRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)


class CopilotResponse(BaseModel):
    answer: str
    evidence_used: list[dict[str, Any]] = []
    disclaimer: str = "This answer is based on data in the LedgerPilot system. Always verify with source records."
