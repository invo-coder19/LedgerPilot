"""Financial record → evidence text chunking.

Converts ORM rows into human-readable text that is suitable for:
  1. Embedding into a vector store
  2. Displaying to users in the Evidence Viewer
  3. Being passed to an LLM in Phase 3B

Each function returns:
  content  : str  — the full text representation
  title    : str  — short identifier for display
  metadata : dict — structured fields for hybrid retrieval filtering
"""

from __future__ import annotations

from datetime import date, datetime


def _fmt_amount(value) -> str:
    """Format a Decimal/float as INR string."""
    if value is None:
        return "N/A"
    try:
        return f"₹{float(value):,.2f}"
    except (TypeError, ValueError):
        return str(value)


def _fmt_date(value) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


# ── Chunkers ──────────────────────────────────────────────────────────────────

def chunk_transaction(tx) -> dict:
    """Convert a Transaction ORM row to evidence text."""
    content = (
        f"Payment {tx.payment_id}\n\n"
        f"Order: {tx.order_id}\n"
        f"Customer: {tx.customer_id or 'N/A'}\n"
        f"Amount: {_fmt_amount(tx.amount)}\n"
        f"Fee: {_fmt_amount(tx.fee)}\n"
        f"Tax: {_fmt_amount(tx.tax)}\n"
        f"Status: {tx.status}\n"
        f"Payment Method: {tx.payment_method or 'N/A'}\n"
        f"Date: {_fmt_date(tx.transaction_timestamp)}"
    )
    return {
        "title": f"Payment {tx.payment_id}",
        "content": content,
        "metadata": {
            "payment_id": tx.payment_id,
            "order_id": tx.order_id,
            "customer_id": tx.customer_id,
            "amount": float(tx.amount) if tx.amount else None,
            "fee": float(tx.fee) if tx.fee else None,
            "status": str(tx.status),
            "payment_method": tx.payment_method,
            "transaction_date": _fmt_date(tx.transaction_timestamp),
        },
    }


def chunk_settlement(stl) -> dict:
    """Convert a Settlement ORM row to evidence text."""
    content = (
        f"Settlement {stl.settlement_id}\n\n"
        f"Payment: {stl.payment_id}\n"
        f"Settlement Amount: {_fmt_amount(stl.settlement_amount)}\n"
        f"Fee: {_fmt_amount(stl.fee)}\n"
        f"Status: {stl.status}\n"
        f"Settlement Date: {_fmt_date(stl.settlement_date)}"
    )
    return {
        "title": f"Settlement {stl.settlement_id}",
        "content": content,
        "metadata": {
            "settlement_id": stl.settlement_id,
            "payment_id": stl.payment_id,
            "settlement_amount": float(stl.settlement_amount) if stl.settlement_amount else None,
            "fee": float(stl.fee) if stl.fee else None,
            "status": str(stl.status),
            "settlement_date": _fmt_date(stl.settlement_date),
        },
    }


def chunk_invoice(inv) -> dict:
    """Convert an Invoice ORM row to evidence text."""
    content = (
        f"Invoice {inv.invoice_id}\n\n"
        f"Customer: {inv.customer_id or 'N/A'}\n"
        f"Amount: {_fmt_amount(inv.amount)}\n"
        f"Tax: {_fmt_amount(inv.tax)}\n"
        f"Status: {inv.status}\n"
        f"Invoice Date: {_fmt_date(inv.invoice_date)}\n"
        f"Due Date: {_fmt_date(inv.due_date)}\n"
        f"Payment Reference: {inv.payment_reference or 'None'}"
    )
    return {
        "title": f"Invoice {inv.invoice_id}",
        "content": content,
        "metadata": {
            "invoice_id": inv.invoice_id,
            "customer_id": inv.customer_id,
            "amount": float(inv.amount) if inv.amount else None,
            "status": str(inv.status),
            "payment_reference": inv.payment_reference,
            "invoice_date": _fmt_date(inv.invoice_date),
            "due_date": _fmt_date(inv.due_date),
        },
    }


def chunk_bank_transaction(bt) -> dict:
    """Convert a BankTransaction ORM row to evidence text."""
    content = (
        f"Bank Transaction {bt.bank_transaction_id}\n\n"
        f"Reference: {bt.reference or 'N/A'}\n"
        f"Amount: {_fmt_amount(bt.amount)}\n"
        f"Type: {bt.transaction_type}\n"
        f"Date: {_fmt_date(bt.transaction_date)}\n"
        f"Description: {bt.description or 'N/A'}"
    )
    return {
        "title": f"Bank Txn {bt.bank_transaction_id}",
        "content": content,
        "metadata": {
            "bank_transaction_id": bt.bank_transaction_id,
            "reference": bt.reference,
            "amount": float(bt.amount) if bt.amount else None,
            "transaction_type": str(bt.transaction_type),
            "transaction_date": _fmt_date(bt.transaction_date),
        },
    }


def chunk_exception(exc) -> dict:
    """Convert a financial Exception ORM row to evidence text."""
    content = (
        f"Exception {exc.id}\n\n"
        f"Type: {exc.exception_type}\n"
        f"Severity: {exc.severity}\n"
        f"Status: {exc.status}\n"
        f"Source: {exc.source_type} / {exc.source_id}\n"
        f"Amount: {_fmt_amount(exc.amount)}\n"
        f"Description: {exc.description}\n"
        f"Created: {_fmt_date(exc.created_at)}"
    )
    return {
        "title": f"Exception {exc.exception_type} ({exc.severity})",
        "content": content,
        "metadata": {
            "exception_id": str(exc.id),
            "exception_type": str(exc.exception_type),
            "severity": str(exc.severity),
            "status": str(exc.status),
            "source_type": exc.source_type,
            "source_id": exc.source_id,
            "amount": float(exc.amount) if exc.amount else None,
        },
    }


def chunk_finance_rule(rule_id: str, title: str, rule_text: str) -> dict:
    """Create an evidence document for a demo finance rule."""
    content = (
        f"DEMO FINANCE RULE — {title}\n\n"
        f"{rule_text}\n\n"
        f"[This is a demonstration rule for LedgerPilot. "
        f"It is not an official policy of any payment gateway or institution.]"
    )
    return {
        "title": f"[DEMO RULE] {title}",
        "content": content,
        "metadata": {
            "rule_id": rule_id,
            "type": "FINANCE_RULE",
            "is_demo": True,
        },
    }


def chunk_historical_case(
    case_id: str,
    description: str,
    resolution: str,
    amount: float | None = None,
) -> dict:
    """Create an evidence document for a synthetic historical resolved case."""
    content = (
        f"Historical Case {case_id}\n\n"
        f"Description:\n{description}\n\n"
        f"Resolution:\n{resolution}"
        + (f"\n\nAmount involved: {_fmt_amount(amount)}" if amount else "")
    )
    return {
        "title": f"Historical Case {case_id}",
        "content": content,
        "metadata": {
            "case_id": case_id,
            "type": "HISTORICAL_CASE",
            "resolution": resolution[:100],
            "amount": amount,
        },
    }
