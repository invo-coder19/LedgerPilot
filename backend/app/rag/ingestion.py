"""Evidence ingestion service.

Converts financial ORM records into EvidenceDocument rows with embeddings.
Called from the seed script and from the intelligence API.

Caching:
  If an evidence document for a given (source_type, source_id, merchant_id)
  already exists AND the content has not changed (same content_hash),
  the existing embedding is reused.  A new embedding is generated only
  when content changes.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models.evidence_document import EvidenceDocument, EvidenceSourceType, EvidenceTrustLevel
from app.models.transaction import Transaction
from app.models.invoice import Invoice
from app.models.settlement import Settlement
from app.models.bank_transaction import BankTransaction
from app.models.exception import Exception as FinancialException
from app.rag import chunking, embeddings
from app.repositories.evidence_document_repository import EvidenceDocumentRepository


# ── Demo Finance Rules ────────────────────────────────────────────────────────

FINANCE_RULES: list[dict] = [
    {
        "id": "RULE_FEE_001",
        "title": "Processing Fee Deduction",
        "text": (
            "A processing fee is deducted from the transaction amount before settlement. "
            "The fee rate is agreed upon in the merchant agreement. "
            "The expected settlement amount = transaction amount − processing fee."
        ),
    },
    {
        "id": "RULE_SETTLE_001",
        "title": "Settlement Timing",
        "text": (
            "Settlement may occur one to two business days after a successful payment. "
            "Weekends and bank holidays may add one to two additional days. "
            "A settlement delayed beyond five business days should be investigated."
        ),
    },
    {
        "id": "RULE_REFUND_001",
        "title": "Refund and Settlement Adjustment",
        "text": (
            "A full refund results in a reversal of the original settlement amount. "
            "A partial refund results in a negative adjustment equal to the refund amount. "
            "Refund processing fees may or may not be returned depending on the merchant agreement."
        ),
    },
    {
        "id": "RULE_FEE_002",
        "title": "Fee Variance Tolerance",
        "text": (
            "A fee difference below 2% of the transaction amount may be treated as a rounding "
            "variance rather than a fee mismatch exception. "
            "Amounts exceeding this tolerance require manual review."
        ),
    },
    {
        "id": "RULE_DUP_001",
        "title": "Duplicate Payment Detection",
        "text": (
            "If the same payment_id appears in two or more settlement records, "
            "one is likely a duplicate. The earlier settlement record is treated as authoritative. "
            "The later record must be investigated and resolved."
        ),
    },
    {
        "id": "RULE_INV_001",
        "title": "Invoice Matching",
        "text": (
            "Every payment must have a corresponding invoice within the accounting period. "
            "A payment without an invoice is flagged as MISSING_INVOICE. "
            "Invoice amounts should match payment amounts within the fee tolerance."
        ),
    },
]

# ── Synthetic Historical Cases ─────────────────────────────────────────────────

HISTORICAL_CASES: list[dict] = [
    {
        "id": "CASE_001",
        "description": (
            "Payment of ₹10,000 settled for ₹9,820. "
            "The settlement was ₹180 less than the payment amount."
        ),
        "resolution": (
            "FEE_VARIANCE — The ₹180 difference matched the agreed 1.8% processing fee. "
            "No discrepancy. Case closed."
        ),
        "amount": 10000.0,
    },
    {
        "id": "CASE_002",
        "description": (
            "The same payment reference PAY-DEMO-991 appeared in two settlement records "
            "on the same day, each for ₹45,000."
        ),
        "resolution": (
            "DUPLICATE — Confirmed duplicate settlement. "
            "One settlement was reversed. Merchant account credited."
        ),
        "amount": 45000.0,
    },
    {
        "id": "CASE_003",
        "description": (
            "Successful payment of ₹75,000 received on 2026-07-01. "
            "No settlement received within 7 business days."
        ),
        "resolution": (
            "MISSING_SETTLEMENT — Payment gateway processing error. "
            "Settlement was manually triggered and completed on 2026-07-10."
        ),
        "amount": 75000.0,
    },
    {
        "id": "CASE_004",
        "description": (
            "Refund of ₹5,200 processed for an original payment of ₹4,800. "
            "Refund amount exceeds original payment."
        ),
        "resolution": (
            "REFUND_MISMATCH — Refund amount was incorrectly entered. "
            "Refund was recalled and reissued for ₹4,800."
        ),
        "amount": 5200.0,
    },
    {
        "id": "CASE_005",
        "description": (
            "Settlement received 12 days after payment date. "
            "Normal window is 1-2 business days."
        ),
        "resolution": (
            "DATE_MISMATCH — Investigation found the payment was held due to "
            "a KYC flag on the merchant account. Flag was cleared; settlement released."
        ),
        "amount": 28500.0,
    },
    {
        "id": "CASE_006",
        "description": (
            "Invoice INV-DEMO-2841 for ₹150,000. "
            "Payment received was ₹92,000 — a shortfall of ₹58,000."
        ),
        "resolution": (
            "AMOUNT_MISMATCH — Customer paid the first installment only. "
            "Invoice split into two; first installment marked PARTIALLY_PAID."
        ),
        "amount": 150000.0,
    },
]


# ── Ingestion helpers ─────────────────────────────────────────────────────────

def _upsert_evidence(
    repo: EvidenceDocumentRepository,
    db: Session,
    source_type: EvidenceSourceType,
    source_id: Optional[str],
    chunk: dict,
    trust_level: EvidenceTrustLevel,
    merchant_id: Optional[uuid.UUID],
) -> EvidenceDocument:
    """Create or update an evidence document and its embedding."""
    content = chunk["content"]
    content_hash = embeddings.compute_content_hash(content)

    existing = repo.get_by_source(source_type, source_id or "", merchant_id)

    if existing is not None:
        # Only re-embed if content changed
        if not embeddings.should_re_embed(existing.content_hash, content):
            return existing
        existing.content = content
        existing.content_hash = content_hash
        existing.title = chunk["title"]
        existing.metadata_ = chunk["metadata"]
        existing.updated_at = datetime.now(timezone.utc)
        doc = existing
    else:
        doc = EvidenceDocument(
            merchant_id=merchant_id,
            source_type=source_type,
            source_id=source_id,
            title=chunk["title"],
            content=content,
            content_hash=content_hash,
            metadata_=chunk["metadata"],
            trust_level=trust_level,
            embedding_dim=384,
        )
        repo.create(doc)

    db.flush()

    # Generate and store embedding
    vec = embeddings.embed_text(content)
    repo.upsert_embedding(doc.id, vec)
    db.commit()
    return doc


# ── Public ingestors ──────────────────────────────────────────────────────────

def ingest_transaction(
    db: Session, tx: Transaction, merchant_id: Optional[uuid.UUID] = None
) -> EvidenceDocument:
    repo = EvidenceDocumentRepository(db)
    chunk = chunking.chunk_transaction(tx)
    return _upsert_evidence(
        repo, db,
        EvidenceSourceType.TRANSACTION, tx.payment_id, chunk,
        EvidenceTrustLevel.PRIMARY, merchant_id,
    )


def ingest_settlement(
    db: Session, stl: Settlement, merchant_id: Optional[uuid.UUID] = None
) -> EvidenceDocument:
    repo = EvidenceDocumentRepository(db)
    chunk = chunking.chunk_settlement(stl)
    return _upsert_evidence(
        repo, db,
        EvidenceSourceType.SETTLEMENT, stl.settlement_id, chunk,
        EvidenceTrustLevel.PRIMARY, merchant_id,
    )


def ingest_invoice(
    db: Session, inv: Invoice, merchant_id: Optional[uuid.UUID] = None
) -> EvidenceDocument:
    repo = EvidenceDocumentRepository(db)
    chunk = chunking.chunk_invoice(inv)
    return _upsert_evidence(
        repo, db,
        EvidenceSourceType.INVOICE, inv.invoice_id, chunk,
        EvidenceTrustLevel.SECONDARY, merchant_id,
    )


def ingest_bank_transaction(
    db: Session, bt: BankTransaction, merchant_id: Optional[uuid.UUID] = None
) -> EvidenceDocument:
    repo = EvidenceDocumentRepository(db)
    chunk = chunking.chunk_bank_transaction(bt)
    return _upsert_evidence(
        repo, db,
        EvidenceSourceType.BANK_TRANSACTION, bt.bank_transaction_id, chunk,
        EvidenceTrustLevel.SECONDARY, merchant_id,
    )


def ingest_exception(
    db: Session, exc: FinancialException, merchant_id: Optional[uuid.UUID] = None
) -> EvidenceDocument:
    repo = EvidenceDocumentRepository(db)
    chunk = chunking.chunk_exception(exc)
    return _upsert_evidence(
        repo, db,
        EvidenceSourceType.EXCEPTION, str(exc.id), chunk,
        EvidenceTrustLevel.PRIMARY, merchant_id,
    )


def ingest_finance_rules(db: Session) -> list[EvidenceDocument]:
    """Ingest all demo finance rules as global evidence (merchant_id=None)."""
    repo = EvidenceDocumentRepository(db)
    docs = []
    for rule in FINANCE_RULES:
        chunk = chunking.chunk_finance_rule(rule["id"], rule["title"], rule["text"])
        doc = _upsert_evidence(
            repo, db,
            EvidenceSourceType.FINANCE_RULE, rule["id"], chunk,
            EvidenceTrustLevel.REFERENCE, None,
        )
        docs.append(doc)
    return docs


def ingest_historical_cases(db: Session) -> list[EvidenceDocument]:
    """Ingest all synthetic historical cases as global evidence (merchant_id=None)."""
    repo = EvidenceDocumentRepository(db)
    docs = []
    for case in HISTORICAL_CASES:
        chunk = chunking.chunk_historical_case(
            case["id"], case["description"], case["resolution"], case.get("amount")
        )
        doc = _upsert_evidence(
            repo, db,
            EvidenceSourceType.HISTORICAL_CASE, case["id"], chunk,
            EvidenceTrustLevel.HISTORICAL, None,
        )
        docs.append(doc)
    return docs
