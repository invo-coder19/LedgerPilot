"""Read-only investigation tools for Phase 3B agent.

Every tool enforces:
  - Merchant ownership / record-level authorization
  - Read-only access (NO write operations)
  - Input sanitization

Tools return simple dicts (not ORM objects) to keep state serializable.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.core.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

_MAX_ITEMS = settings.AI_MAX_CONTEXT_ITEMS


def _truncate(text: Optional[str], max_len: int = 500) -> str:
    if not text:
        return ""
    return text[:max_len] + ("…" if len(text) > max_len else "")


class InvestigationTools:
    """All read-only tools for the investigation agent.

    This class is instantiated once per investigation run,
    scoped to a specific merchant_id for isolation.
    """

    def __init__(self, db: Session, merchant_id: Optional[uuid.UUID]) -> None:
        self.db = db
        self.merchant_id = merchant_id

    # ── Exception ─────────────────────────────────────────────────────────────

    def get_exception(self, exception_id: str) -> dict:
        """Load an exception by ID. Enforces merchant isolation."""
        from app.models.exception import Exception as FinancialException
        try:
            exc_uuid = uuid.UUID(exception_id)
        except ValueError:
            return {"error": "Invalid exception ID"}

        exc = self.db.get(FinancialException, exc_uuid)
        if exc is None:
            return {"error": "Exception not found"}
        if self.merchant_id and exc.merchant_id != self.merchant_id:
            return {"error": "Access denied"}

        return {
            "id": str(exc.id),
            "exception_type": str(exc.exception_type.value),
            "severity": str(exc.severity.value),
            "status": str(exc.status.value),
            "source_type": exc.source_type,
            "source_id": exc.source_id,
            "amount": float(exc.amount) if exc.amount else None,
            "description": _truncate(exc.description),
            "merchant_id": str(exc.merchant_id),
        }

    # ── Transaction ───────────────────────────────────────────────────────────

    def get_transaction(self, payment_id: str) -> dict:
        """Load transaction by payment_id."""
        from app.models.transaction import Transaction
        tx = (
            self.db.query(Transaction)
            .filter(Transaction.payment_id == payment_id)
            .first()
        )
        if tx is None:
            return {"error": f"Transaction not found: {payment_id}"}
        if self.merchant_id and tx.merchant_id != self.merchant_id:
            return {"error": "Access denied"}

        return {
            "id": str(tx.id),
            "payment_id": tx.payment_id,
            "order_id": tx.order_id,
            "amount": float(tx.amount) if tx.amount else None,
            "fee": float(tx.fee) if tx.fee else None,
            "tax": float(tx.tax) if tx.tax else None,
            "status": str(tx.status.value),
            "payment_method": tx.payment_method,
            "timestamp": str(tx.transaction_timestamp) if tx.transaction_timestamp else None,
        }

    # ── Invoice ───────────────────────────────────────────────────────────────

    def get_invoice(self, invoice_id: str) -> dict:
        """Load invoice by invoice_id."""
        from app.models.invoice import Invoice
        inv = (
            self.db.query(Invoice)
            .filter(Invoice.invoice_id == invoice_id)
            .first()
        )
        if inv is None:
            return {"error": f"Invoice not found: {invoice_id}"}
        if self.merchant_id and inv.merchant_id != self.merchant_id:
            return {"error": "Access denied"}

        return {
            "id": str(inv.id),
            "invoice_id": inv.invoice_id,
            "amount": float(inv.amount) if inv.amount else None,
            "tax": float(inv.tax) if inv.tax else None,
            "status": str(inv.status.value),
            "invoice_date": str(inv.invoice_date) if inv.invoice_date else None,
            "due_date": str(inv.due_date) if inv.due_date else None,
            "payment_reference": inv.payment_reference,
        }

    # ── Settlement ────────────────────────────────────────────────────────────

    def get_settlement(self, settlement_id: str) -> dict:
        """Load settlement by settlement_id."""
        from app.models.settlement import Settlement
        stl = (
            self.db.query(Settlement)
            .filter(Settlement.settlement_id == settlement_id)
            .first()
        )
        if stl is None:
            return {"error": f"Settlement not found: {settlement_id}"}
        if self.merchant_id and stl.merchant_id != self.merchant_id:
            return {"error": "Access denied"}

        return {
            "id": str(stl.id),
            "settlement_id": stl.settlement_id,
            "payment_id": stl.payment_id,
            "settlement_amount": float(stl.settlement_amount) if stl.settlement_amount else None,
            "fee": float(stl.fee) if stl.fee else None,
            "status": str(stl.status.value),
            "settlement_date": str(stl.settlement_date) if stl.settlement_date else None,
        }

    # ── Bank Transaction ──────────────────────────────────────────────────────

    def get_bank_transaction(self, bank_transaction_id: str) -> dict:
        """Load bank transaction by bank_transaction_id."""
        from app.models.bank_transaction import BankTransaction
        bt = (
            self.db.query(BankTransaction)
            .filter(BankTransaction.bank_transaction_id == bank_transaction_id)
            .first()
        )
        if bt is None:
            return {"error": f"Bank transaction not found: {bank_transaction_id}"}
        if self.merchant_id and bt.merchant_id != self.merchant_id:
            return {"error": "Access denied"}

        return {
            "id": str(bt.id),
            "bank_transaction_id": bt.bank_transaction_id,
            "reference": bt.reference,
            "amount": float(bt.amount) if bt.amount else None,
            "transaction_type": str(bt.transaction_type.value),
            "transaction_date": str(bt.transaction_date) if bt.transaction_date else None,
            "description": _truncate(bt.description),
        }

    # ── Evidence search ───────────────────────────────────────────────────────

    def search_evidence(
        self,
        query: str,
        top_k: int = 7,
        source_types: Optional[list[str]] = None,
    ) -> list[dict]:
        """Semantic evidence search, merchant-scoped."""
        from app.rag.retriever import EvidenceRetriever
        try:
            retriever = EvidenceRetriever(self.db)
            results = retriever.search(
                query=query,
                merchant_id=self.merchant_id,
                top_k=min(top_k, _MAX_ITEMS),
                source_types=source_types,
            )
            return results[:_MAX_ITEMS]
        except Exception as exc:
            logger.warning("Evidence search failed: %s", exc)
            return []

    # ── Finance rules ─────────────────────────────────────────────────────────

    def get_finance_rules(self, query: str = "financial exception processing fee settlement") -> list[dict]:
        """Retrieve relevant finance rules for the investigation."""
        return self.search_evidence(query=query, top_k=6, source_types=["FINANCE_RULE"])

    # ── Historical cases ──────────────────────────────────────────────────────

    def get_similar_cases(self, description: str) -> list[dict]:
        """Retrieve similar historical resolved cases."""
        return self.search_evidence(query=description, top_k=4, source_types=["HISTORICAL_CASE"])

    # ── Related records ───────────────────────────────────────────────────────

    def get_related_records(self, source_id: str, exception_type: str) -> dict:
        """Get all financial records related to a payment_id."""
        from app.models.settlement import Settlement
        from app.models.invoice import Invoice

        settlements = (
            self.db.query(Settlement)
            .filter(Settlement.payment_id == source_id)
            .limit(5)
            .all()
        )
        invoices = (
            self.db.query(Invoice)
            .filter(Invoice.payment_reference == source_id)
            .limit(3)
            .all()
        )

        tx = self.get_transaction(source_id)

        return {
            "transaction": tx,
            "settlements": [
                {
                    "settlement_id": s.settlement_id,
                    "settlement_amount": float(s.settlement_amount) if s.settlement_amount else None,
                    "fee": float(s.fee) if s.fee else None,
                    "status": str(s.status.value),
                    "settlement_date": str(s.settlement_date) if s.settlement_date else None,
                }
                for s in settlements
            ],
            "invoices": [
                {
                    "invoice_id": i.invoice_id,
                    "amount": float(i.amount) if i.amount else None,
                    "status": str(i.status.value),
                    "payment_reference": i.payment_reference,
                }
                for i in invoices
            ],
        }

    # ── ML prediction ─────────────────────────────────────────────────────────

    def get_ml_prediction(self, entity_type: str, entity_id: str) -> dict:
        """Get the latest ML prediction for an entity."""
        from app.models.ml_prediction import ModelType
        from app.repositories.ml_prediction_repository import MLPredictionRepository

        repo = MLPredictionRepository(self.db)
        pred = repo.get_latest_for_entity(entity_type, entity_id, ModelType.EXCEPTION_CLASSIFIER)
        if pred is None:
            return {"available": False}

        return {
            "available": True,
            "predicted_type": pred.prediction,
            "confidence": float(pred.confidence) if pred.confidence else None,
            "model_version": pred.model_version,
            "top_alternatives": pred.top_alternatives or [],
        }
