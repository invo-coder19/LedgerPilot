"""Settlement model and status enum."""

import enum
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import Date, DateTime, Enum, Index, Numeric, String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class SettlementStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSED = "PROCESSED"
    FAILED = "FAILED"


class Settlement(Base):
    __tablename__ = "settlements"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    merchant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("merchants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    settlement_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    payment_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    settlement_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    fee: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0"))
    settlement_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[SettlementStatus] = mapped_column(
        Enum(SettlementStatus), nullable=False, default=SettlementStatus.PENDING, index=True
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
    merchant: Mapped["Merchant"] = relationship("Merchant", back_populates="settlements")  # noqa: F821

    __table_args__ = (
        Index("ix_settlements_merchant_status", "merchant_id", "status"),
    )

    def __repr__(self) -> str:
        return f"<Settlement {self.settlement_id} {self.status}>"
