"""Phase 4 — Pydantic schemas for controller API."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.schemas.common import ORMBase


# ── Controller Run ────────────────────────────────────────────────────────────

class ControllerRunCreate(BaseModel):
    reconciliation_run_id: Optional[str] = None
    dry_run: bool = False


class ControllerRunResponse(ORMBase):
    id: str
    merchant_id: str
    reconciliation_run_id: Optional[str] = None
    status: str
    dry_run: bool = False
    total_exceptions: int = 0
    processed: int = 0
    auto_executed: int = 0
    recommended: int = 0
    escalated: int = 0
    blocked: int = 0
    failed: int = 0
    amount_processed: float = 0
    amount_auto_resolved: float = 0
    amount_awaiting_review: float = 0
    amount_escalated: float = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    error_message: Optional[str] = None


class ControllerRunListResponse(ORMBase):
    total: int
    page: int
    page_size: int
    pages: int
    items: list[ControllerRunResponse]


# ── Controller Decision ───────────────────────────────────────────────────────

class ControllerDecisionResponse(ORMBase):
    id: str
    controller_run_id: str
    exception_id: str
    investigation_id: Optional[str] = None
    decision: str
    action: Optional[str] = None
    confidence: float = 0.0
    risk_score: float = 1.0
    risk_band: str = "CRITICAL"
    reason: str = ""
    evidence_ids: Optional[list[str]] = None
    policy_version: Optional[str] = None
    requires_approval: bool = True
    status: str = "PENDING"
    risk_details: Optional[dict[str, Any]] = None
    dry_run: bool = False
    created_at: datetime


class ControllerDecisionListResponse(ORMBase):
    total: int
    page: int
    page_size: int
    pages: int
    items: list[ControllerDecisionResponse]


# ── Approval ──────────────────────────────────────────────────────────────────

class ApprovalResponse(ORMBase):
    id: str
    exception_id: str
    decision_id: str
    requested_action: str
    amount: Optional[float] = None
    risk_score: float
    confidence: float
    reason: str
    status: str
    requested_at: datetime
    expires_at: Optional[datetime] = None
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    rejected_by: Optional[str] = None
    rejected_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None


class ApprovalListResponse(ORMBase):
    total: int
    page: int
    page_size: int
    pages: int
    items: list[ApprovalResponse]


class ApproveRequest(BaseModel):
    """Empty body — approval is just a POST."""
    pass


class RejectRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=2000, description="Rejection reason is required")


# ── Policy ────────────────────────────────────────────────────────────────────

class PolicyResponse(ORMBase):
    id: str
    policy_id: str
    version: int
    name: str
    description: str
    configuration: dict[str, Any]
    status: str
    created_at: datetime
    created_by: Optional[str] = None


class PolicyListResponse(ORMBase):
    total: int
    items: list[PolicyResponse]


class PolicyCreateRequest(BaseModel):
    policy_id: str = Field(min_length=1, max_length=128)
    name: str = Field(min_length=1, max_length=255)
    description: str = ""
    configuration: dict[str, Any]


class PolicyUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    configuration: Optional[dict[str, Any]] = None


# ── Action Result ─────────────────────────────────────────────────────────────

class ActionResultResponse(ORMBase):
    id: str
    decision_id: str
    exception_id: str
    action: str
    idempotency_key: str
    status: str
    previous_state: Optional[str] = None
    new_state: Optional[str] = None
    policy_version: Optional[str] = None
    executed_by: str
    verified: bool = False
    verification_details: Optional[dict[str, Any]] = None
    error_message: Optional[str] = None
    is_reversible: bool = False
    rolled_back: bool = False
    rolled_back_at: Optional[datetime] = None
    executed_at: datetime


class ActionResultListResponse(ORMBase):
    total: int
    page: int
    page_size: int
    pages: int
    items: list[ActionResultResponse]


# ── Controller Config ─────────────────────────────────────────────────────────

class ControllerConfigResponse(BaseModel):
    kill_switch: bool = False
    max_auto_amount: float = 10000.0
    max_auto_per_run: int = 500
    max_auto_per_hour: int = 1000
    max_concurrent: int = 10
    dry_run_default: bool = False


class ControllerConfigUpdate(BaseModel):
    kill_switch: Optional[bool] = None
    max_auto_amount: Optional[float] = None
    max_auto_per_run: Optional[int] = None
    max_auto_per_hour: Optional[int] = None
    max_concurrent: Optional[int] = None
    dry_run_default: Optional[bool] = None


# ── Controller Metrics ────────────────────────────────────────────────────────

class ControllerMetricsResponse(BaseModel):
    operational: dict[str, Any]
    financial: dict[str, Any]
    quality: dict[str, Any]


# ── Decision Distribution (for charts) ────────────────────────────────────────

class DecisionDistributionItem(BaseModel):
    decision: str
    count: int


class ActionOutcomeItem(BaseModel):
    status: str
    count: int


# ── Error ─────────────────────────────────────────────────────────────────────

class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Optional[dict[str, Any]] = None


class ErrorResponse(BaseModel):
    error: ErrorDetail
