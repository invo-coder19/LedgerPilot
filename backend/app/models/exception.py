"""Financial exception model with type, severity, and status enums.

Note: The class is named ``Exception`` to match the domain concept.
Python's built-in ``Exception`` is shadowed locally — import this model
as ``FinancialException`` where clarity is needed.
"""

import enum
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import DateTime, Enum, Index, Numeric, String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ExceptionType(str, enum.Enum):
    AMOUNT_MISMATCH = "AMOUNT_MISMATCH"
    MISSING_INVOICE = "MISSING_INVOICE"
    MISSING_SETTLEMENT = "MISSING_SETTLEMENT"
    DUPLICATE = "DUPLICATE"
    REFUND_MISMATCH = "REFUND_MISMATCH"
    UNKNOWN = "UNKNOWN"


class ExceptionSeverity(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ExceptionStatus(str, enum.Enum):
    OPEN = "OPEN"
    IN_REVIEW = "IN_REVIEW"
    RESOLVED = "RESOLVED"
    DISMISSED = "DISMISSED"


class Exception(Base):  # noqa: A001  (intentional domain naming)
    __tablename__ = "exceptions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    merchant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("merchants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_id: Mapped[str] = mapped_column(String(128), nullable=False)
    exception_type: Mapped[ExceptionType] = mapped_column(
        Enum(ExceptionType), nullable=False, index=True
    )
    severity: Mapped[ExceptionSeverity] = mapped_column(
        Enum(ExceptionSeverity), nullable=False, index=True
    )
    amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[ExceptionStatus] = mapped_column(
        Enum(ExceptionStatus), nullable=False, default=ExceptionStatus.OPEN, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    merchant: Mapped["Merchant"] = relationship("Merchant", back_populates="exceptions")  # noqa: F821

    __table_args__ = (
        Index("ix_exceptions_merchant_status", "merchant_id", "status"),
        Index("ix_exceptions_merchant_severity", "merchant_id", "severity"),
    )

    def __repr__(self) -> str:
        return f"<Exception {self.exception_type} {self.severity} {self.status}>"
