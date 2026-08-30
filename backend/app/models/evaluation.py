"""Phase 5 — Evaluation ORM models.

Tables:
  evaluation_datasets — versioned benchmark datasets (ground truth)
  evaluation_runs     — individual evaluation executions
  evaluation_results  — metric name/value rows per run (queryable)
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    JSON, Boolean, DateTime, Enum, Float, Integer, String, Text,
    ForeignKey, Index, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class EvaluationStatus(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class EvaluationDataset(Base):
    """A versioned benchmark dataset containing ground-truth cases."""
    __tablename__ = "evaluation_datasets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    record_count: Mapped[int] = mapped_column(Integer, default=0)
    random_seed: Mapped[int] = mapped_column(Integer, nullable=True)
    distribution: Mapped[dict] = mapped_column(JSON, nullable=True)
    # Split info: train/validation/test/benchmark percentages
    split_config: Mapped[dict] = mapped_column(JSON, nullable=True)
    # The actual cases stored as JSON array
    cases: Mapped[list] = mapped_column(JSON, nullable=True)
    # Metadata: model versions, git commit, policy version
    metadata_: Mapped[dict] = mapped_column("metadata", JSON, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    runs: Mapped[list["EvaluationRun"]] = relationship(
        "EvaluationRun", back_populates="dataset", lazy="dynamic"
    )

    __table_args__ = (
        UniqueConstraint("name", "version", name="uq_eval_dataset_name_version"),
        Index("ix_eval_datasets_name", "name"),
    )


class EvaluationRun(Base):
    """An evaluation execution against a specific dataset."""
    __tablename__ = "evaluation_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("evaluation_datasets.id"), nullable=False
    )
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[EvaluationStatus] = mapped_column(
        Enum(EvaluationStatus, name="evaluation_status"),
        default=EvaluationStatus.PENDING,
    )
    records_tested: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Versions recorded for reproducibility
    configuration: Mapped[dict] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    dataset: Mapped["EvaluationDataset"] = relationship(
        "EvaluationDataset", back_populates="runs"
    )
    results: Mapped[list["EvaluationResult"]] = relationship(
        "EvaluationResult", back_populates="run", lazy="dynamic"
    )

    __table_args__ = (
        Index("ix_eval_runs_dataset_id", "dataset_id"),
        Index("ix_eval_runs_status", "status"),
    )


class EvaluationResult(Base):
    """A single metric measurement for an evaluation run."""
    __tablename__ = "evaluation_results"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    evaluation_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("evaluation_runs.id"), nullable=False
    )
    metric_name: Mapped[str] = mapped_column(String(128), nullable=False)
    metric_value: Mapped[float] = mapped_column(Float, nullable=False)
    metric_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    category: Mapped[str] = mapped_column(String(64), nullable=True)  # reconciliation/ml/ai/controller/financial
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    run: Mapped["EvaluationRun"] = relationship("EvaluationRun", back_populates="results")

    __table_args__ = (
        Index("ix_eval_results_run_id", "evaluation_run_id"),
        UniqueConstraint("evaluation_run_id", "metric_name", name="uq_eval_result_run_metric"),
    )
