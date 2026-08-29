"""Hybrid evidence retriever.

Combines:
  1. Metadata filtering (merchant_id, source_type, payment_id)
  2. Semantic similarity via pgvector cosine distance

The retriever is designed to be queried by the intelligence API
and later by the LangGraph agent in Phase 3B.
"""

from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy.orm import Session

from app.rag.embeddings import embed_text
from app.repositories.evidence_document_repository import EvidenceDocumentRepository


class EvidenceRetriever:
    """Hybrid retriever: metadata filter + semantic similarity."""

    def __init__(self, db: Session) -> None:
        self.repo = EvidenceDocumentRepository(db)

    def search(
        self,
        query: str,
        merchant_id: Optional[uuid.UUID],
        top_k: int = 7,
        source_types: Optional[list[str]] = None,
    ) -> list[dict]:
        """Semantic search with merchant-level isolation.

        Parameters
        ----------
        query        : Natural-language query string
        merchant_id  : Scope results to this merchant (+ global records)
        top_k        : Number of results to return
        source_types : Optional filter by source type (e.g. ["TRANSACTION"])

        Returns
        -------
        list of dicts with: id, source_type, source_id, title, content,
          metadata, trust_level, similarity_score
        """
        query_vec = embed_text(query)
        return self.repo.semantic_search(
            query_embedding=query_vec,
            merchant_id=merchant_id,
            top_k=top_k,
            source_types=source_types,
        )

    def search_for_payment(
        self,
        payment_id: str,
        merchant_id: Optional[uuid.UUID],
        top_k: int = 10,
    ) -> list[dict]:
        """Retrieve all evidence directly related to a payment_id.

        First retrieves records matching payment_id exactly (structured),
        then falls back to semantic similarity for context.
        """
        # 1. Exact payment_id records (transactions, settlements)
        exact = self.repo.semantic_search(
            query_embedding=embed_text(f"Payment {payment_id}"),
            merchant_id=merchant_id,
            top_k=top_k,
            source_id_filter=payment_id,
        )
        # 2. Semantic context (finance rules, historical cases)
        semantic = self.repo.semantic_search(
            query_embedding=embed_text(f"Payment {payment_id} discrepancy"),
            merchant_id=merchant_id,
            top_k=max(3, top_k - len(exact)),
            source_types=["FINANCE_RULE", "HISTORICAL_CASE"],
        )
        # Deduplicate by id
        seen = {r["id"] for r in exact}
        combined = list(exact)
        for r in semantic:
            if r["id"] not in seen:
                combined.append(r)
                seen.add(r["id"])
        return combined

    def build_exception_evidence_bundle(
        self,
        exception_id: str,
        source_id: str,
        merchant_id: Optional[uuid.UUID],
        description: str,
        top_k: int = 10,
    ) -> dict:
        """Build a full evidence bundle for an exception.

        Returns a structured dict containing:
          transaction_evidence, settlement_evidence, invoice_evidence,
          bank_evidence, finance_rules, historical_cases, all_evidence
        """
        # Get related financial records by payment/source ID
        related = self.repo.semantic_search(
            query_embedding=embed_text(f"Payment {source_id} settlement invoice"),
            merchant_id=merchant_id,
            top_k=top_k,
            source_types=["TRANSACTION", "SETTLEMENT", "INVOICE", "BANK_TRANSACTION"],
        )

        # Finance rules relevant to the exception
        rules = self.repo.semantic_search(
            query_embedding=embed_text(description),
            merchant_id=None,
            top_k=4,
            source_types=["FINANCE_RULE"],
        )

        # Similar historical cases
        cases = self.repo.semantic_search(
            query_embedding=embed_text(description),
            merchant_id=None,
            top_k=3,
            source_types=["HISTORICAL_CASE"],
        )

        # Partition by type
        tx_ev = [r for r in related if r["source_type"] == "TRANSACTION"]
        stl_ev = [r for r in related if r["source_type"] == "SETTLEMENT"]
        inv_ev = [r for r in related if r["source_type"] == "INVOICE"]
        bank_ev = [r for r in related if r["source_type"] == "BANK_TRANSACTION"]

        all_evidence = related + rules + cases

        return {
            "transaction_evidence": tx_ev,
            "settlement_evidence": stl_ev,
            "invoice_evidence": inv_ev,
            "bank_evidence": bank_ev,
            "finance_rules": rules,
            "historical_cases": cases,
            "all_evidence": all_evidence,
            "counts": {
                "transactions": len(tx_ev),
                "settlements": len(stl_ev),
                "invoices": len(inv_ev),
                "bank_transactions": len(bank_ev),
                "finance_rules": len(rules),
                "historical_cases": len(cases),
                "total": len(all_evidence),
            },
        }
