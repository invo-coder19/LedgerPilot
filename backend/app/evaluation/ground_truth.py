"""Ground-truth schema for evaluation cases.

Ground truth is NEVER exposed to the inference pipeline.
It is only used during offline evaluation to compare expected vs actual.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class GroundTruthCase:
    """A single ground-truth evaluation case."""

    case_id: str
    scenario_type: str  # clean_match | fee_variance | amount_mismatch | duplicate | ...

    # Reconciliation ground truth
    expected_match_status: str  # MATCHED | UNMATCHED | PARTIAL
    expected_exception_type: Optional[str] = None  # FEE_VARIANCE | AMOUNT_MISMATCH | ...
    expected_root_cause: Optional[str] = None       # FEE_VARIANCE | DUPLICATE | UNKNOWN | ...
    expected_action_class: str = "NO_ACTION"        # NO_ACTION | AUTO_RESOLVE_ALLOWED | HUMAN_REVIEW | BLOCK

    # Financial context (for cost calculation)
    amount: float = 0.0
    financial_impact: float = 0.0  # Amount at stake if wrong

    # Synthetic data references
    transaction_id: Optional[str] = None
    invoice_id: Optional[str] = None
    settlement_id: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "case_id": self.case_id,
            "scenario_type": self.scenario_type,
            "expected_match_status": self.expected_match_status,
            "expected_exception_type": self.expected_exception_type,
            "expected_root_cause": self.expected_root_cause,
            "expected_action_class": self.expected_action_class,
            "amount": self.amount,
            "financial_impact": self.financial_impact,
            "transaction_id": self.transaction_id,
            "invoice_id": self.invoice_id,
            "settlement_id": self.settlement_id,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "GroundTruthCase":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ── Scenario type → expected classification mapping ──────────────────────────

SCENARIO_GROUND_TRUTH: dict[str, dict] = {
    "clean_match": {
        "expected_match_status": "MATCHED",
        "expected_exception_type": None,
        "expected_root_cause": None,
        "expected_action_class": "NO_ACTION",
    },
    "fee_variance": {
        "expected_match_status": "PARTIAL",
        "expected_exception_type": "FEE_VARIANCE",
        "expected_root_cause": "FEE_VARIANCE",
        "expected_action_class": "AUTO_RESOLVE_ALLOWED",
    },
    "amount_mismatch": {
        "expected_match_status": "UNMATCHED",
        "expected_exception_type": "AMOUNT_MISMATCH",
        "expected_root_cause": "AMOUNT_MISMATCH",
        "expected_action_class": "HUMAN_REVIEW",
    },
    "duplicate": {
        "expected_match_status": "UNMATCHED",
        "expected_exception_type": "DUPLICATE",
        "expected_root_cause": "DUPLICATE",
        "expected_action_class": "HUMAN_REVIEW",
    },
    "missing_invoice": {
        "expected_match_status": "UNMATCHED",
        "expected_exception_type": "MISSING_INVOICE",
        "expected_root_cause": "MISSING_INVOICE",
        "expected_action_class": "HUMAN_REVIEW",
    },
    "missing_settlement": {
        "expected_match_status": "UNMATCHED",
        "expected_exception_type": "MISSING_SETTLEMENT",
        "expected_root_cause": "MISSING_SETTLEMENT",
        "expected_action_class": "HUMAN_REVIEW",
    },
    "refund_mismatch": {
        "expected_match_status": "UNMATCHED",
        "expected_exception_type": "REFUND_MISMATCH",
        "expected_root_cause": "REFUND_MISMATCH",
        "expected_action_class": "HUMAN_REVIEW",
    },
    "date_mismatch": {
        "expected_match_status": "PARTIAL",
        "expected_exception_type": "DATE_MISMATCH",
        "expected_root_cause": "DATE_MISMATCH",
        "expected_action_class": "AUTO_RESOLVE_ALLOWED",
    },
    "ambiguous": {
        "expected_match_status": "UNMATCHED",
        "expected_exception_type": "AMOUNT_MISMATCH",
        "expected_root_cause": "UNKNOWN",
        "expected_action_class": "HUMAN_REVIEW",
    },
}
