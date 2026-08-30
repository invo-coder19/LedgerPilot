"""Deterministic risk scoring engine.

The risk score is computed ENTIRELY by this module using quantifiable signals.
No LLM, no prompt, no opaque logic.

Risk Score Formula
==================
    risk_score = (
        amount_risk     * 0.30
      + evidence_risk   * 0.25
      + uncertainty_risk* 0.20
      + exception_risk  * 0.15
      + model_risk      * 0.10
    )

    Normalised to [0.0, 1.0]

Risk Bands
==========
    LOW:      < 0.25
    MEDIUM:   0.25 – 0.50
    HIGH:     0.50 – 0.75
    CRITICAL: >= 0.75
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional

from app.models.controller import RiskBand

logger = logging.getLogger(__name__)

# ── Weights (sum = 1.0) ──────────────────────────────────────────────────────
_WEIGHTS = {
    "amount": 0.30,
    "evidence": 0.25,
    "uncertainty": 0.20,
    "exception_type": 0.15,
    "model": 0.10,
}

# ── Risk band thresholds (configurable via policy) ────────────────────────────
DEFAULT_BAND_THRESHOLDS = {
    "LOW": 0.25,
    "MEDIUM": 0.50,
    "HIGH": 0.75,
}

# ── Amount risk tiers ─────────────────────────────────────────────────────────
DEFAULT_AMOUNT_TIERS = [
    (1000, 0.1),
    (5000, 0.3),
    (10000, 0.5),
    (50000, 0.7),
    (100000, 0.9),
]

# ── Exception type base risk ─────────────────────────────────────────────────
_EXCEPTION_TYPE_RISK = {
    "AMOUNT_MISMATCH": 0.3,
    "MISSING_INVOICE": 0.5,
    "MISSING_SETTLEMENT": 0.5,
    "DUPLICATE": 0.6,
    "REFUND_MISMATCH": 0.5,
    "UNKNOWN": 1.0,
}


@dataclass
class RiskComponents:
    """Breakdown of the deterministic risk computation."""
    amount_risk: float = 0.0
    evidence_risk: float = 0.0
    uncertainty_risk: float = 0.0
    exception_risk: float = 0.0
    model_risk: float = 0.0
    details: dict = field(default_factory=dict)


@dataclass
class RiskAssessment:
    """Final risk assessment output."""
    risk_score: float
    risk_band: RiskBand
    components: RiskComponents
    details: dict


def compute_amount_risk(
    amount: Optional[Decimal],
    tiers: list[tuple[float, float]] | None = None,
) -> float:
    """Score financial risk based on transaction amount.

    Higher amounts → higher risk.  None amount → moderate risk (0.5).
    """
    if amount is None:
        return 0.5
    amt = float(amount)
    if amt <= 0:
        return 0.0
    tiers = tiers or DEFAULT_AMOUNT_TIERS
    for threshold, risk in tiers:
        if amt <= threshold:
            return risk
    return 1.0


def compute_evidence_risk(
    evidence_count: int,
    avg_trust: float,
    has_primary_evidence: bool,
) -> float:
    """Score risk based on evidence quality and quantity.

    Less/lower-quality evidence → higher risk.
    """
    if evidence_count == 0:
        return 1.0
    count_score = max(0.0, 1.0 - (evidence_count / 5.0))
    trust_score = max(0.0, 1.0 - avg_trust)
    primary_bonus = 0.0 if has_primary_evidence else 0.2
    return min(1.0, count_score * 0.4 + trust_score * 0.4 + primary_bonus)


def compute_uncertainty_risk(
    contradiction_detected: bool,
    uncertainty_count: int,
    requires_human: bool,
) -> float:
    """Score risk from contradictions and uncertainties."""
    risk = 0.0
    if contradiction_detected:
        risk += 0.5
    risk += min(uncertainty_count * 0.1, 0.3)
    if requires_human:
        risk += 0.2
    return min(1.0, risk)


def compute_exception_type_risk(exception_type: str) -> float:
    """Score inherent risk for the exception category."""
    return _EXCEPTION_TYPE_RISK.get(exception_type, 0.7)


def compute_model_risk(
    ml_confidence: Optional[float],
    ai_confidence: float,
    ml_agrees_with_ai: bool,
) -> float:
    """Score risk from model uncertainty or disagreement."""
    risk = 0.0
    if ml_confidence is None:
        risk += 0.3
    elif ml_confidence < 0.6:
        risk += 0.3 * (1.0 - ml_confidence)
    if not ml_agrees_with_ai:
        risk += 0.3
    if ai_confidence < 0.7:
        risk += 0.3 * (1.0 - ai_confidence)
    return min(1.0, risk)


def classify_risk_band(
    score: float,
    thresholds: dict[str, float] | None = None,
) -> RiskBand:
    """Map a risk score to a risk band."""
    t = thresholds or DEFAULT_BAND_THRESHOLDS
    if score < t.get("LOW", 0.25):
        return RiskBand.LOW
    if score < t.get("MEDIUM", 0.50):
        return RiskBand.MEDIUM
    if score < t.get("HIGH", 0.75):
        return RiskBand.HIGH
    return RiskBand.CRITICAL


def assess_risk(
    amount: Optional[Decimal],
    evidence_count: int,
    avg_trust: float,
    has_primary_evidence: bool,
    contradiction_detected: bool,
    uncertainty_count: int,
    requires_human: bool,
    exception_type: str,
    ml_confidence: Optional[float],
    ai_confidence: float,
    ml_agrees_with_ai: bool,
    amount_tiers: list[tuple[float, float]] | None = None,
    band_thresholds: dict[str, float] | None = None,
) -> RiskAssessment:
    """Compute a comprehensive deterministic risk assessment.

    Returns a RiskAssessment with score ∈ [0, 1], band, and full breakdown.
    """
    components = RiskComponents(
        amount_risk=compute_amount_risk(amount, amount_tiers),
        evidence_risk=compute_evidence_risk(evidence_count, avg_trust, has_primary_evidence),
        uncertainty_risk=compute_uncertainty_risk(contradiction_detected, uncertainty_count, requires_human),
        exception_risk=compute_exception_type_risk(exception_type),
        model_risk=compute_model_risk(ml_confidence, ai_confidence, ml_agrees_with_ai),
    )

    raw = (
        components.amount_risk * _WEIGHTS["amount"]
        + components.evidence_risk * _WEIGHTS["evidence"]
        + components.uncertainty_risk * _WEIGHTS["uncertainty"]
        + components.exception_risk * _WEIGHTS["exception_type"]
        + components.model_risk * _WEIGHTS["model"]
    )
    score = round(max(0.0, min(1.0, raw)), 4)
    band = classify_risk_band(score, band_thresholds)

    components.details = {
        "amount_risk": round(components.amount_risk, 4),
        "evidence_risk": round(components.evidence_risk, 4),
        "uncertainty_risk": round(components.uncertainty_risk, 4),
        "exception_risk": round(components.exception_risk, 4),
        "model_risk": round(components.model_risk, 4),
        "weights": _WEIGHTS,
        "final_score": score,
        "band": band.value,
    }

    logger.debug(
        "Risk assessed: score=%.4f band=%s amount=%s type=%s",
        score, band.value, amount, exception_type,
    )

    return RiskAssessment(
        risk_score=score,
        risk_band=band,
        components=components,
        details=components.details,
    )
