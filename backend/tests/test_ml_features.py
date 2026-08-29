"""Tests for Phase 3A feature engineering."""

import math
from datetime import date, timedelta
from decimal import Decimal

import numpy as np
import pytest

from app.ml.features import (
    FEATURE_NAMES,
    extract_features,
    features_to_array,
    records_to_dataframe,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def clean_record():
    today = date.today()
    return {
        "amount": Decimal("10000.00"),
        "fee": Decimal("200.00"),
        "tax": Decimal("36.00"),
        "settlement_amount": Decimal("9800.00"),
        "transaction_date": today,
        "settlement_date": today + timedelta(days=1),
        "status": "SUCCESS",
        "payment_method": "UPI",
        "has_invoice": True,
        "has_settlement": True,
        "has_bank_credit": True,
    }


# ── Feature name tests ─────────────────────────────────────────────────────────

def test_feature_names_count():
    assert len(FEATURE_NAMES) == 16


def test_feature_names_are_unique():
    assert len(FEATURE_NAMES) == len(set(FEATURE_NAMES))


# ── Extraction tests ──────────────────────────────────────────────────────────

def test_extract_features_returns_all_keys(clean_record):
    features = extract_features(clean_record)
    assert set(features.keys()) == set(FEATURE_NAMES)


def test_extract_features_correct_amount(clean_record):
    features = extract_features(clean_record)
    assert features["amount"] == pytest.approx(10000.0)


def test_extract_features_fee_ratio(clean_record):
    features = extract_features(clean_record)
    # fee=200, amount=10000 → ratio=0.02
    assert features["fee_ratio"] == pytest.approx(0.02, abs=1e-6)


def test_extract_features_settlement_diff(clean_record):
    features = extract_features(clean_record)
    # amount=10000, settlement=9800 → diff=200
    assert features["amount_vs_settlement_diff"] == pytest.approx(200.0, abs=0.01)


def test_extract_features_settlement_delay(clean_record):
    features = extract_features(clean_record)
    # settlement_date = transaction_date + 1 day
    assert features["settlement_delay_days"] == pytest.approx(1.0)


def test_extract_features_payment_method_upi(clean_record):
    features = extract_features(clean_record)
    assert features["payment_method_encoded"] == 0.0  # UPI → 0


def test_extract_features_payment_method_rtgs(clean_record):
    clean_record["payment_method"] = "RTGS"
    features = extract_features(clean_record)
    assert features["payment_method_encoded"] == 3.0  # RTGS → 3


def test_extract_features_unknown_payment_method(clean_record):
    clean_record["payment_method"] = "BARTER"
    features = extract_features(clean_record)
    assert features["payment_method_encoded"] == 7.0  # UNKNOWN → 7


def test_extract_features_refund_status():
    rec = {"status": "REFUNDED", "payment_method": "UPI"}
    features = extract_features(rec)
    assert features["is_refund"] == 1.0
    assert features["is_failed"] == 0.0


def test_extract_features_failed_status():
    rec = {"status": "FAILED", "payment_method": "NEFT"}
    features = extract_features(rec)
    assert features["is_failed"] == 1.0
    assert features["is_refund"] == 0.0


def test_extract_features_boolean_flags(clean_record):
    features = extract_features(clean_record)
    assert features["has_invoice"] == 1.0
    assert features["has_settlement"] == 1.0
    assert features["has_bank_credit"] == 1.0


def test_extract_features_missing_flags():
    features = extract_features({"has_invoice": False, "has_settlement": False})
    assert features["has_invoice"] == 0.0
    assert features["has_settlement"] == 0.0


# ── Missing values ────────────────────────────────────────────────────────────

def test_extract_features_handles_none_amount():
    features = extract_features({"amount": None})
    assert features["amount"] == 0.0
    assert math.isfinite(features["fee_ratio"])


def test_extract_features_handles_empty_record():
    features = extract_features({})
    for k, v in features.items():
        assert math.isfinite(v), f"Feature '{k}' is not finite: {v}"


def test_extract_features_handles_zero_amount():
    features = extract_features({"amount": 0, "fee": 10})
    # fee_ratio with zero denominator → 0.0
    assert features["fee_ratio"] == 0.0
    assert math.isfinite(features["fee_ratio"])


def test_extract_features_extreme_amounts():
    features = extract_features({"amount": 1e12, "fee": 1e10})
    assert math.isfinite(features["fee_ratio"])


def test_extract_features_nan_not_in_output(clean_record):
    features = extract_features(clean_record)
    for k, v in features.items():
        assert not math.isnan(v), f"NaN in feature '{k}'"
        assert not math.isinf(v), f"Inf in feature '{k}'"


# ── Ratio capping ─────────────────────────────────────────────────────────────

def test_fee_ratio_capped_at_1():
    # fee > amount
    features = extract_features({"amount": 100, "fee": 500})
    assert features["fee_ratio"] <= 1.0


def test_rel_amount_diff_capped_at_1():
    # huge discrepancy
    features = extract_features({"amount": 100, "settlement_amount": 10000})
    assert features["rel_amount_diff"] <= 1.0


# ── Decimal precision ─────────────────────────────────────────────────────────

def test_decimal_amount_converts_correctly():
    features = extract_features({"amount": Decimal("12345.6789")})
    assert features["amount"] == pytest.approx(12345.6789, rel=1e-6)


# ── Array / DataFrame ─────────────────────────────────────────────────────────

def test_features_to_array_length(clean_record):
    features = extract_features(clean_record)
    arr = features_to_array(features)
    assert arr.shape == (len(FEATURE_NAMES),)


def test_features_to_array_dtype(clean_record):
    features = extract_features(clean_record)
    arr = features_to_array(features)
    assert arr.dtype == np.float32


def test_records_to_dataframe_shape():
    records = [{}, {"amount": 1000}, {"amount": 2000, "fee": 50}]
    df = records_to_dataframe(records)
    assert df.shape == (3, len(FEATURE_NAMES))
    assert list(df.columns) == FEATURE_NAMES


def test_records_to_dataframe_no_nan():
    records = [{"amount": None}, {}, {"fee": None, "tax": None}]
    df = records_to_dataframe(records)
    assert not df.isnull().any().any()
