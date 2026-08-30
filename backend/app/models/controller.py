"""Phase 4 — Autonomous Controller ORM models.

Tables:
  controller_runs        — batch controller execution records
  controller_decisions   — per-exception decision + action
  approval_requests      — human approval workflow
  controller_policies    — versioned policy definitions
  action_results         — executed action records (idempotent)
  controller_config      — global safety limits and kill switch
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    Boolean, DateTime, Enum, Float, Index, Integer, Numeric,
    String, Text, ForeignKey, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


# ── Enums ─────────────────────────────────────────────────────────────────────

class ControllerRunStatus(str, enum.Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class ControllerDecisionType(str, enum.Enum):
    AUTO_EXECUTE = "AUTO_EXECUTE"
    RECOMMEND = "RECOMMEND"
    ESCALATE = "ESCALATE"
    BLOCK = "BLOCK"


class ControllerDecisionStatus(str, enum.Enum):
    PENDING = "PENDING"
    EXECUTED = "EXECUTED"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    REJECTED = "REJECTED"
    ESCALATED = "ESCALATED"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"


class ApprovalStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


class PolicyStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class ActionStatus(str, enum.Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    FAILED_VERIFICATION = "FAILED_VERIFICATION"
    ROLLED_BACK = "ROLLED_BACK"


class RiskBand(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


# ── Controller Run ────────────────────────────────────────────────────────────

class ControllerRun(Base):
    __tablename__ = "controller_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    merchant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("merchants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reconciliation_run_id: Mapped[str | None] = mapped_column(
        String(128), nullable=True, index=True,
    )
    status: Mapped[ControllerRunStatus] = mapped_column(
        Enum(ControllerRunStatus),
        nullable=False,
        default=ControllerRunStatus.QUEUED,
        index=True,
    )
    dry_run: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False,
    )
    total_exceptions: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
    )
    processed: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
    )
    auto_executed: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
    )
    recommended: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
    )
    escalated: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
    )
    blocked: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
    )
    failed: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
    )
    amount_processed: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, default=0,
    )
    amount_auto_resolved: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, default=0,
    )
    amount_awaiting_review: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, default=0,
    )
    amount_escalated: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, default=0,
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Relationships ─────────────────────────────────────────────────────────
    decisions: Mapped[list["ControllerDecision"]] = relationship(
        "ControllerDecision",
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="ControllerDecision.created_at",
    )

    def __repr__(self) -> str:
        return f"<ControllerRun {self.id} status={self.status}>"


# ── Controller Decision ───────────────────────────────────────────────────────

class ControllerDecision(Base):
    __tablename__ = "controller_decisions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    controller_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("controller_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    exception_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("exceptions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    investigation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ai_investigation_runs.id", ondelete="SET NULL"),
        nullable=True,
    )
    decision: Mapped[ControllerDecisionType] = mapped_column(
        Enum(ControllerDecisionType), nullable=False, index=True,
    )
    action: Mapped[str | None] = mapped_column(String(128), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    risk_score: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    risk_band: Mapped[RiskBand] = mapped_column(
        Enum(RiskBand), nullable=False, default=RiskBand.CRITICAL,
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False, default="")
    evidence_ids: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    policy_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    requires_approval: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True,
    )
    status: Mapped[ControllerDecisionStatus] = mapped_column(
        Enum(ControllerDecisionStatus),
        nullable=False,
        default=ControllerDecisionStatus.PENDING,
        index=True,
    )
    risk_details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    dry_run: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    run: Mapped[ControllerRun] = relationship(
        "ControllerRun", back_populates="decisions",
    )

    __table_args__ = (
        Index("ix_ctrl_decision_exc", "exception_id", "controller_run_id"),
    )

    def __repr__(self) -> str:
        return f"<ControllerDecision {self.decision} risk={self.risk_band}>"


# ── Approval Request ──────────────────────────────────────────────────────────

class ApprovalRequest(Base):
    __tablename__ = "approval_requests"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    exception_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("exceptions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    decision_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("controller_decisions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    requested_action: Mapped[str] = mapped_column(String(128), nullable=False)
    amount: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 4), nullable=True,
    )
    risk_score: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[ApprovalStatus] = mapped_column(
        Enum(ApprovalStatus),
        nullable=False,
        default=ApprovalStatus.PENDING,
        index=True,
    )
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    approved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    rejected_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    rejected_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_approval_status_requested", "status", "requested_at"),
    )

    def __repr__(self) -> str:
        return f"<ApprovalRequest {self.id} status={self.status}>"


# ── Controller Policy ─────────────────────────────────────────────────────────

class ControllerPolicy(Base):
    __tablename__ = "controller_policies"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    policy_id: Mapped[str] = mapped_column(
        String(128), nullable=False, index=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    # JSON configuration: thresholds, exception_types, allowed_actions, etc.
    configuration: Mapped[dict] = mapped_column(JSONB, nullable=False)
    status: Mapped[PolicyStatus] = mapped_column(
        Enum(PolicyStatus),
        nullable=False,
        default=PolicyStatus.ACTIVE,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    __table_args__ = (
        UniqueConstraint("policy_id", "version", name="uq_policy_id_version"),
        Index("ix_policy_active", "policy_id", "status"),
    )

    def __repr__(self) -> str:
        return f"<ControllerPolicy {self.policy_id} v{self.version} {self.status}>"


# ── Action Result ─────────────────────────────────────────────────────────────

class ActionResult(Base):
    __tablename__ = "action_results"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    decision_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("controller_decisions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    exception_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("exceptions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    # Idempotency key: exception_id + action + decision_id
    idempotency_key: Mapped[str] = mapped_column(
        String(512), nullable=False, unique=True,
    )
    status: Mapped[ActionStatus] = mapped_column(
        Enum(ActionStatus), nullable=False, index=True,
    )
    previous_state: Mapped[str | None] = mapped_column(String(64), nullable=True)
    new_state: Mapped[str | None] = mapped_column(String(64), nullable=True)
    policy_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    executed_by: Mapped[str] = mapped_column(
        String(128), nullable=False, default="system",
    )
    verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    verification_details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_reversible: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False,
    )
    rolled_back: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False,
    )
    rolled_back_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    executed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return f"<ActionResult {self.action} {self.status}>"


# ── Controller Config ─────────────────────────────────────────────────────────

class ControllerConfig(Base):
    """Singleton-like key-value configuration for the autonomous controller.

    Keys:
        kill_switch         — bool, blocks all autonomous actions
        max_auto_amount     — float, max amount for auto-execution
        max_auto_per_run    — int, max auto actions per controller run
        max_auto_per_hour   — int, max auto actions per hour
        max_concurrent      — int, max concurrent action executions
        dry_run_default     — bool, default dry-run mode
    """
    __tablename__ = "controller_config"

    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    value: Mapped[dict] = mapped_column(JSONB, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    def __repr__(self) -> str:
        return f"<ControllerConfig {self.key}>"
