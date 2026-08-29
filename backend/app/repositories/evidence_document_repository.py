"""Evidence document repository — wraps pgvector similarity search.

Uses raw SQL for the VECTOR cosine similarity queries since SQLAlchemy
does not have native pgvector type support out of the box.
All merchant-scoped queries include merchant_id in the WHERE clause
to enforce data isolation.
"""

from __future__ import annotations

import uuid
from typing import Any, Optional

import sqlalchemy as sa
from sqlalchemy.orm import Session

from app.models.evidence_document import EvidenceDocument, EvidenceSourceType, EvidenceTrustLevel


class EvidenceDocumentRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    # ── Write ──────────────────────────────────────────────────────────────────

    def create(self, doc: EvidenceDocument) -> EvidenceDocument:
        self.db.add(doc)
        self.db.flush()
        return doc

    def upsert_embedding(self, doc_id: uuid.UUID, embedding: list[float]) -> None:
        """Store the vector embedding for an evidence document."""
        vec_str = "[" + ",".join(str(v) for v in embedding) + "]"
        self.db.execute(
            sa.text(
                "UPDATE evidence_documents "
                "SET embedding = :vec::vector "
                "WHERE id = :id"
            ),
            {"vec": vec_str, "id": str(doc_id)},
        )

    # ── Read ───────────────────────────────────────────────────────────────────

    def get_by_id(self, doc_id: uuid.UUID) -> Optional[EvidenceDocument]:
        return self.db.get(EvidenceDocument, doc_id)

    def get_by_source(
        self,
        source_type: EvidenceSourceType,
        source_id: str,
        merchant_id: Optional[uuid.UUID] = None,
    ) -> Optional[EvidenceDocument]:
        q = self.db.query(EvidenceDocument).filter(
            EvidenceDocument.source_type == source_type,
            EvidenceDocument.source_id == source_id,
        )
        if merchant_id is not None:
            q = q.filter(
                (EvidenceDocument.merchant_id == merchant_id)
                | (EvidenceDocument.merchant_id.is_(None))
            )
        return q.first()

    def list_by_merchant(
        self,
        merchant_id: uuid.UUID,
        source_type: Optional[EvidenceSourceType] = None,
        limit: int = 50,
    ) -> list[EvidenceDocument]:
        q = self.db.query(EvidenceDocument).filter(
            (EvidenceDocument.merchant_id == merchant_id)
            | (EvidenceDocument.merchant_id.is_(None))
        )
        if source_type is not None:
            q = q.filter(EvidenceDocument.source_type == source_type)
        return q.order_by(EvidenceDocument.created_at.desc()).limit(limit).all()

    # ── Semantic search ───────────────────────────────────────────────────────

    def semantic_search(
        self,
        query_embedding: list[float],
        merchant_id: Optional[uuid.UUID],
        top_k: int = 5,
        source_types: Optional[list[str]] = None,
        source_id_filter: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """Hybrid semantic + metadata search using pgvector cosine similarity.

        Returns list of dicts with keys:
          id, source_type, source_id, title, content, metadata,
          trust_level, similarity_score
        """
        vec_str = "[" + ",".join(str(v) for v in query_embedding) + "]"

        # Build WHERE conditions
        conditions = ["embedding IS NOT NULL"]
        params: dict = {"vec": vec_str, "top_k": top_k}

        if merchant_id is not None:
            conditions.append(
                "(merchant_id = :merchant_id OR merchant_id IS NULL)"
            )
            params["merchant_id"] = str(merchant_id)

        if source_types:
            # Build IN clause
            placeholders = ", ".join(f":st_{i}" for i in range(len(source_types)))
            conditions.append(f"source_type IN ({placeholders})")
            for i, st in enumerate(source_types):
                params[f"st_{i}"] = st

        if source_id_filter:
            conditions.append("source_id = :source_id_filter")
            params["source_id_filter"] = source_id_filter

        where_clause = " AND ".join(conditions)

        sql = sa.text(f"""
            SELECT
                id::text,
                source_type,
                source_id,
                title,
                content,
                metadata,
                trust_level,
                1 - (embedding <=> :vec::vector) AS similarity_score
            FROM evidence_documents
            WHERE {where_clause}
            ORDER BY embedding <=> :vec::vector
            LIMIT :top_k
        """)

        rows = self.db.execute(sql, params).mappings().all()
        return [dict(r) for r in rows]

    def count_by_source_type(
        self, merchant_id: Optional[uuid.UUID] = None
    ) -> dict[str, int]:
        """Count evidence documents per source type."""
        q = self.db.query(
            EvidenceDocument.source_type,
            sa.func.count(EvidenceDocument.id).label("cnt"),
        )
        if merchant_id is not None:
            q = q.filter(
                (EvidenceDocument.merchant_id == merchant_id)
                | (EvidenceDocument.merchant_id.is_(None))
            )
        rows = q.group_by(EvidenceDocument.source_type).all()
        return {r[0]: r[1] for r in rows}
