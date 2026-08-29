"""Synthetic ML dataset generator for Phase 3A.

Generates 2,000+ labeled financial cases with realistic feature distributions.
The class distribution is configurable via CLASS_WEIGHTS.

CRITICAL — data leakage prevention:
  The train/val/test split is performed BEFORE any preprocessing fitting.
  The scaler/encoder is ONLY fitted on the training split.
  Validation and test splits are transformed with the training-fitted scaler.

Label taxonomy (aligned with ExceptionType ORM enum + Phase 3A additions):
  NORMAL              — Clean reconciliation
  FEE_VARIANCE        — Fee discrepancy within small tolerance
  AMOUNT_MISMATCH     — Significant amount discrepancy
  MISSING_INVOICE     — No invoice found for payment
  MISSING_SETTLEMENT  — Payment not settled
  DUPLICATE           — Duplicate reference detected
  REFUND_MISMATCH     — Refund amount inconsistent
  DATE_MISMATCH       — Settlement date outside expected window
  UNKNOWN             — Unclassifiable anomaly
"""

from __future__ import annotations

import random
from datetime import date, timedelta
from decimal import Decimal

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

from app.core.config import get_settings
from app.ml.features import FEATURE_NAMES, records_to_dataframe

SEED = 42

# Class weights define how many samples each class gets
CLASS_WEIGHTS: dict[str, int] = {
    "NORMAL": 900,
    "FEE_VARIANCE": 230,
    "AMOUNT_MISMATCH": 200,
    "MISSING_INVOICE": 180,
    "MISSING_SETTLEMENT": 180,
    "DUPLICATE": 130,
    "REFUND_MISMATCH": 100,
    "DATE_MISMATCH": 80,
    "UNKNOWN": 50,
}

PAYMENT_METHODS = ["UPI", "NEFT", "IMPS", "RTGS", "Card", "NetBanking", "Wallet"]


def _rng() -> random.Random:
    return random.Random(SEED)


def _np_rng() -> np.random.Generator:
    return np.random.default_rng(SEED)


# ── Per-class synthetic record generators ─────────────────────────────────────

def _base_record(rng: random.Random, np_rng: np.random.Generator) -> dict:
    amount = round(rng.uniform(500, 200_000), 2)
    fee = round(amount * rng.uniform(0.015, 0.025), 2)
    tax = round(fee * 0.18, 2)
    tx_date = date.today() - timedelta(days=rng.randint(1, 90))
    return {
        "amount": amount,
        "fee": fee,
        "tax": tax,
        "settlement_amount": amount - fee,
        "transaction_date": tx_date,
        "settlement_date": tx_date + timedelta(days=rng.randint(0, 2)),
        "status": "SUCCESS",
        "payment_method": rng.choice(PAYMENT_METHODS),
        "has_invoice": True,
        "has_settlement": True,
        "has_bank_credit": True,
    }


def _generate_class(label: str, n: int, rng: random.Random, np_rng: np.random.Generator) -> list[dict]:
    records = []
    for _ in range(n):
        rec = _base_record(rng, np_rng)
        if label == "NORMAL":
            pass  # clean record as-is

        elif label == "FEE_VARIANCE":
            # Fee slightly off — settlement differs by small amount
            wrong_fee = rec["fee"] * rng.uniform(0.85, 1.15)
            rec["settlement_amount"] = rec["amount"] - wrong_fee

        elif label == "AMOUNT_MISMATCH":
            # Large discrepancy between amount and settlement
            rec["settlement_amount"] = rec["amount"] * rng.uniform(0.6, 0.92)

        elif label == "MISSING_INVOICE":
            rec["has_invoice"] = False
            rec["settlement_amount"] = rec["amount"] - rec["fee"]

        elif label == "MISSING_SETTLEMENT":
            rec["has_settlement"] = False
            rec["settlement_amount"] = 0.0
            rec["has_bank_credit"] = False

        elif label == "DUPLICATE":
            # Very close amounts — possible duplicate
            rec2_amount = rec["amount"] * rng.uniform(0.995, 1.005)
            rec["settlement_amount"] = rec2_amount - rec["fee"]
            rec["amount_vs_settlement_diff_hint"] = "duplicate"

        elif label == "REFUND_MISMATCH":
            rec["status"] = rng.choice(["REFUNDED", "PARTIAL_REFUND"])
            # Refund exceeds original
            rec["settlement_amount"] = -rec["amount"] * rng.uniform(0.8, 1.2)
            rec["is_refund"] = 1.0

        elif label == "DATE_MISMATCH":
            # Settlement date far outside normal window
            delay = rng.randint(8, 45)
            rec["settlement_date"] = rec["transaction_date"] + timedelta(days=delay)

        elif label == "UNKNOWN":
            # Random unusual combination
            rec["amount"] = rec["amount"] * rng.uniform(0.1, 0.3)
            rec["fee"] = rec["fee"] * rng.uniform(2.0, 5.0)
            rec["has_invoice"] = rng.choice([True, False])

        records.append(rec)
    return records


# ── Public API ────────────────────────────────────────────────────────────────

def generate_dataset(
    class_weights: dict[str, int] | None = None,
    seed: int = SEED,
) -> tuple[pd.DataFrame, list[str]]:
    """Generate a labeled synthetic dataset.

    Returns
    -------
    (X_df, y_labels) where X_df has FEATURE_NAMES columns and
    y_labels is the string class for each row.
    """
    if class_weights is None:
        class_weights = CLASS_WEIGHTS

    rng = random.Random(seed)
    np_rng = np.random.default_rng(seed)

    all_records: list[dict] = []
    all_labels: list[str] = []

    for label, n in class_weights.items():
        records = _generate_class(label, n, rng, np_rng)
        all_records.extend(records)
        all_labels.extend([label] * n)

    X_df = records_to_dataframe(all_records)

    # Shuffle with fixed seed
    indices = list(range(len(all_labels)))
    rng.shuffle(indices)
    X_df = X_df.iloc[indices].reset_index(drop=True)
    y_labels = [all_labels[i] for i in indices]

    return X_df, y_labels


def train_val_test_split(
    X: pd.DataFrame,
    y: list[str],
    val_ratio: float = 0.15,
    test_ratio: float = 0.15,
    seed: int = SEED,
) -> tuple[
    pd.DataFrame, pd.DataFrame, pd.DataFrame,
    list[str], list[str], list[str]
]:
    """Split dataset into train/val/test BEFORE any preprocessing.

    Proportions: 70% train / 15% val / 15% test (defaults).
    Stratified split ensures class balance across splits.
    """
    X_arr = X.values

    X_temp, X_test, y_temp, y_test = train_test_split(
        X_arr, y, test_size=test_ratio, stratify=y, random_state=seed
    )
    adjusted_val = val_ratio / (1 - test_ratio)
    X_train, X_val, y_train, y_val = train_test_split(
        X_temp, y_temp, test_size=adjusted_val, stratify=y_temp, random_state=seed
    )

    cols = FEATURE_NAMES
    return (
        pd.DataFrame(X_train, columns=cols),
        pd.DataFrame(X_val, columns=cols),
        pd.DataFrame(X_test, columns=cols),
        list(y_train),
        list(y_val),
        list(y_test),
    )


if __name__ == "__main__":
    X_df, y = generate_dataset()
    print(f"Generated {len(y)} samples")
    from collections import Counter
    dist = Counter(y)
    for cls, cnt in sorted(dist.items()):
        print(f"  {cls:25s}: {cnt}")
