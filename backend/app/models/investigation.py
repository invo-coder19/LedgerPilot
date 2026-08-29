"""ORM models for AI investigation runs and steps.

Phase 3B persists every investigation so it can be:
  - Audited
  - Displayed in the UI timeline
  - Compared against ground truth in evaluation
  - Consumed by Phase 4 for bounded autonomous actions

Tables:
  ai_investigation_runs   — one record per investigation
  ai_investigation_steps  — one record per graph node / tool call
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class InvestigationStatus(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class AIInvestigationRun(Base):
    __tablename__ = "ai_investigation_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    exception_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("exceptions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    merchant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("merchants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status: Mapped[InvestigationStatus] = mapped_column(
        Enum(InvestigationStatus), nullable=False, default=InvestigationStatus.PENDING
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    model_provider: Mapped[str | None] = mapped_column(String(32), nullable=True)
    model_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    model_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # Final structured result (InvestigationResult Pydantic schema as JSON)
    final_result: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    final_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence_band: Mapped[str | None] = mapped_column(String(16), nullable=True)
    requires_human: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Duration in milliseconds
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # ── Relationships ──────────────────────────────────────────────────────────
    steps: Mapped[list["AIInvestigationStep"]] = relationship(
        "AIInvestigationStep",
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="AIInvestigationStep.created_at",
    )

    def __repr__(self) -> str:
        return f"<AIInvestigationRun {self.id} status={self.status}>"


class AIInvestigationStep(Base):
    __tablename__ = "ai_investigation_steps"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    investigation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ai_investigation_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    step_name: Mapped[str] = mapped_column(String(128), nullable=False)
    tool_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    # Short summary of inputs (no secrets, no full records)
    input_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Short summary of outputs
    output_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # ── Relationships ──────────────────────────────────────────────────────────
    run: Mapped[AIInvestigationRun] = relationship(
        "AIInvestigationRun", back_populates="steps"
    )

    def __repr__(self) -> str:
        return f"<AIInvestigationStep {self.step_name}>"
