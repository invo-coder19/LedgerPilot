"""Feature engineering for ML models.

All feature extraction lives here so training and inference use
identical transformations.  No ground-truth labels are included
in the feature vectors — they are handled separately in dataset.py.

Feature semantics:
  amount                      — Transaction/settlement amount (INR)
  fee                         — Declared fee
  tax                         — Declared tax
  fee_ratio                   — fee / amount (capped at 1.0)
  tax_ratio                   — tax / amount (capped at 1.0)
  amount_vs_settlement_diff   — amount − settlement_amount (signed)
  abs_amount_diff             — |amount − settlement_amount|
  rel_amount_diff             — |diff| / amount (capped at 1.0)
  settlement_delay_days       — settlement_date − transaction_date in days
  is_refund                   — 1 if status in {REFUNDED, PARTIAL_REFUND} else 0
  is_failed                   — 1 if status == FAILED else 0
  is_pending                  — 1 if status == PENDING else 0
  payment_method_encoded      — label-encoded payment method
  has_invoice                 — 1 if an invoice exists for this payment
  has_settlement              — 1 if a settlement exists for this payment
  has_bank_credit             — 1 if a matching bank credit exists
"""

from __future__ import annotations

import math
from decimal import Decimal
from typing import Any

import numpy as np
import pandas as pd

# ── Constants ─────────────────────────────────────────────────────────────────

FEATURE_NAMES: list[str] = [
    "amount",
    "fee",
    "tax",
    "fee_ratio",
    "tax_ratio",
    "amount_vs_settlement_diff",
    "abs_amount_diff",
    "rel_amount_diff",
    "settlement_delay_days",
    "is_refund",
    "is_failed",
    "is_pending",
    "payment_method_encoded",
    "has_invoice",
    "has_settlement",
    "has_bank_credit",
]

_PAYMENT_METHOD_MAP: dict[str, int] = {
    "UPI": 0,
    "NEFT": 1,
    "IMPS": 2,
    "RTGS": 3,
    "Card": 4,
    "NetBanking": 5,
    "Wallet": 6,
    "UNKNOWN": 7,
}

_REFUND_STATUSES = {"REFUNDED", "PARTIAL_REFUND"}
_FAILED_STATUSES = {"FAILED"}
_PENDING_STATUSES = {"PENDING"}


# ── Helper ────────────────────────────────────────────────────────────────────

def _to_float(value: Any, default: float = 0.0) -> float:
    """Safely convert Decimal / str / None to float."""
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_ratio(numerator: float, denominator: float, cap: float = 1.0) -> float:
    """Return numerator/denominator, defaulting to 0 on zero-division, capped."""
    if denominator == 0:
        return 0.0
    ratio = numerator / denominator
    return min(abs(ratio), cap)


# ── Main feature extractor ────────────────────────────────────────────────────

def extract_features(record: dict[str, Any]) -> dict[str, float]:
    """Extract a fixed-length feature vector from a financial record dict.

    Parameters
    ----------
    record : dict
        Keys (all optional — missing values are handled gracefully):
          amount, fee, tax, settlement_amount, settlement_date,
          transaction_date, status, payment_method,
          has_invoice, has_settlement, has_bank_credit

    Returns
    -------
    dict[str, float]
        Feature name → float value.  Guaranteed to have all FEATURE_NAMES keys.
    """
    amount = _to_float(record.get("amount"), 0.0)
    fee = _to_float(record.get("fee"), 0.0)
    tax = _to_float(record.get("tax"), 0.0)
    settlement_amount = _to_float(record.get("settlement_amount"), amount)

    # Ratios
    fee_ratio = _safe_ratio(fee, amount)
    tax_ratio = _safe_ratio(tax, amount)

    # Amount discrepancy
    diff = amount - settlement_amount
    abs_diff = abs(diff)
    rel_diff = _safe_ratio(abs_diff, amount)

    # Settlement delay
    tx_date = record.get("transaction_date")
    stl_date = record.get("settlement_date")
    delay_days = 0.0
    if tx_date is not None and stl_date is not None:
        try:
            delta = (stl_date - tx_date).days
            delay_days = float(delta)
        except (TypeError, AttributeError):
            delay_days = 0.0
    # Clamp extreme delays
    delay_days = max(-30.0, min(delay_days, 365.0))

    # Status flags
    status = str(record.get("status", "")).upper()
    is_refund = 1.0 if status in _REFUND_STATUSES else 0.0
    is_failed = 1.0 if status in _FAILED_STATUSES else 0.0
    is_pending = 1.0 if status in _PENDING_STATUSES else 0.0

    # Payment method encoding
    payment_method = str(record.get("payment_method", "UNKNOWN") or "UNKNOWN")
    method_code = float(_PAYMENT_METHOD_MAP.get(payment_method, 7))

    # Boolean presence flags
    has_invoice = 1.0 if record.get("has_invoice") else 0.0
    has_settlement = 1.0 if record.get("has_settlement") else 0.0
    has_bank_credit = 1.0 if record.get("has_bank_credit") else 0.0

    features = {
        "amount": amount,
        "fee": fee,
        "tax": tax,
        "fee_ratio": fee_ratio,
        "tax_ratio": tax_ratio,
        "amount_vs_settlement_diff": diff,
        "abs_amount_diff": abs_diff,
        "rel_amount_diff": rel_diff,
        "settlement_delay_days": delay_days,
        "is_refund": is_refund,
        "is_failed": is_failed,
        "is_pending": is_pending,
        "payment_method_encoded": method_code,
        "has_invoice": has_invoice,
        "has_settlement": has_settlement,
        "has_bank_credit": has_bank_credit,
    }

    # Final safety pass — replace NaN/Inf
    for k, v in features.items():
        if not math.isfinite(v):
            features[k] = 0.0

    return features


def records_to_dataframe(records: list[dict[str, Any]]) -> pd.DataFrame:
    """Convert a list of record dicts to a feature DataFrame."""
    rows = [extract_features(r) for r in records]
    return pd.DataFrame(rows, columns=FEATURE_NAMES)


def features_to_array(features: dict[str, float]) -> np.ndarray:
    """Return a 1-D numpy array in FEATURE_NAMES order."""
    return np.array([features[k] for k in FEATURE_NAMES], dtype=np.float32)
