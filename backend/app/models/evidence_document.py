"""Evidence document model — stores financial records as searchable text with vector embeddings.

Used by the RAG (Retrieval-Augmented Generation) layer.
The ``embedding`` column requires the pgvector PostgreSQL extension.
"""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class EvidenceSourceType(str, enum.Enum):
    TRANSACTION = "TRANSACTION"
    INVOICE = "INVOICE"
    SETTLEMENT = "SETTLEMENT"
    BANK_TRANSACTION = "BANK_TRANSACTION"
    EXCEPTION = "EXCEPTION"
    FINANCE_RULE = "FINANCE_RULE"       # Demo business rules (labelled DEMO)
    HISTORICAL_CASE = "HISTORICAL_CASE" # Synthetic resolved cases


class EvidenceTrustLevel(str, enum.Enum):
    PRIMARY = "PRIMARY"        # Directly related financial record
    SECONDARY = "SECONDARY"    # Related financial record
    REFERENCE = "REFERENCE"    # Finance rule / policy
    HISTORICAL = "HISTORICAL"  # Similar resolved case


class EvidenceDocument(Base):
    __tablename__ = "evidence_documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    merchant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    source_type: Mapped[EvidenceSourceType] = mapped_column(
        Enum(EvidenceSourceType), nullable=False, index=True
    )
    source_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)

    title: Mapped[str] = mapped_column(String(512), nullable=False)
    # Human-readable text representation — this is what gets embedded
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # Hash of content — used to detect if re-embedding is needed
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Structured metadata for hybrid filtering (amount, date, payment_id, etc.)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)

    trust_level: Mapped[EvidenceTrustLevel] = mapped_column(
        Enum(EvidenceTrustLevel), nullable=False, default=EvidenceTrustLevel.SECONDARY
    )

    # pgvector embedding — dimension set at migration time (384 for all-MiniLM-L6-v2)
    # Stored as a native vector column via pgvector; SQLAlchemy accesses via text/raw
    # We use a nullable Text column here for ORM compatibility;
    # the actual VECTOR type is applied by the migration and raw SQL helpers.
    # The embedding is stored in a separate column accessed directly by the retriever.
    embedding_dim: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        Index("ix_evidence_merchant_source", "merchant_id", "source_type"),
        Index("ix_evidence_source_id", "source_type", "source_id"),
    )

    def __repr__(self) -> str:
        return f"<EvidenceDocument {self.source_type} {self.source_id}>"
