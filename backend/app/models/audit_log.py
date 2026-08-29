"""Audit log model and action enum."""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class AuditAction(str, enum.Enum):
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    VIEW_TRANSACTION = "VIEW_TRANSACTION"
    VIEW_INVOICE = "VIEW_INVOICE"
    VIEW_SETTLEMENT = "VIEW_SETTLEMENT"
    VIEW_BANK_TRANSACTION = "VIEW_BANK_TRANSACTION"
    VIEW_EXCEPTION = "VIEW_EXCEPTION"
    UPDATE_EXCEPTION = "UPDATE_EXCEPTION"
    APPROVE_ACTION = "APPROVE_ACTION"
    REJECT_ACTION = "REJECT_ACTION"
    VIEW_AUDIT_LOG = "VIEW_AUDIT_LOG"
    VIEW_DASHBOARD = "VIEW_DASHBOARD"
    # ── Phase 3A: Intelligence ─────────────────────────────────────────────────────
    ML_ANALYSIS_REQUESTED = "ML_ANALYSIS_REQUESTED"
    ML_ANALYSIS_COMPLETED = "ML_ANALYSIS_COMPLETED"
    EVIDENCE_SEARCHED = "EVIDENCE_SEARCHED"
    EVIDENCE_VIEWED = "EVIDENCE_VIEWED"
    INTELLIGENCE_CONTEXT_VIEWED = "INTELLIGENCE_CONTEXT_VIEWED"
    # ── Phase 3B: AI Investigation ──────────────────────────────────────────────
    AI_INVESTIGATION_STARTED = "AI_INVESTIGATION_STARTED"
    AI_EVIDENCE_RETRIEVED = "AI_EVIDENCE_RETRIEVED"
    AI_INVESTIGATION_COMPLETED = "AI_INVESTIGATION_COMPLETED"
    AI_INVESTIGATION_FAILED = "AI_INVESTIGATION_FAILED"
    COPILOT_QUERY = "COPILOT_QUERY"


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    merchant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("merchants.id", ondelete="SET NULL"), nullable=True, index=True
    )
    action: Mapped[AuditAction] = mapped_column(Enum(AuditAction), nullable=False, index=True)
    entity_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    entity_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), index=True
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    user: Mapped["User"] = relationship("User", back_populates="audit_logs")  # noqa: F821
    merchant: Mapped["Merchant"] = relationship("Merchant", back_populates="audit_logs")  # noqa: F821

    def __repr__(self) -> str:
        return f"<AuditLog {self.action} by user={self.user_id}>"
