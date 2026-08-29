"""Confidence policy and safety policies for Phase 3B agent.

The confidence score is computed DETERMINISTICALLY by this module, NOT by the LLM.
The LLM provides a raw signal (5% weight) but the final score is policy-driven.

This ensures:
  - Auditable, reproducible confidence scores
  - LLM cannot inflate confidence to avoid human review
  - Contradiction detection automatically caps confidence
  - Weights are centralized — not scattered in prompts

Weights (sum = 1.0):
  evidence_quality:     0.30
  ml_support:           0.20
  anomaly_agreement:    0.20
  rule_match:           0.15
  historical_match:     0.10
  llm_signal:           0.05
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from app.core.config import get_settings

# Weight table (must sum to 1.0)
_WEIGHTS = {
    "evidence_quality": 0.30,
    "ml_support": 0.20,
    "anomaly_agreement": 0.20,
    "rule_match": 0.15,
    "historical_match": 0.10,
    "llm_signal": 0.05,
}

# Trust level weights for evidence quality
_TRUST_WEIGHTS = {
    "PRIMARY": 1.0,
    "SECONDARY": 0.7,
    "REFERENCE": 0.5,
    "HISTORICAL": 0.4,
}

SAFETY_BOUNDARY_ACTIONS = frozenset([
    "approve", "reject", "refund", "settle", "mark_reconciled",
    "auto_resolve", "send_email", "trigger_payment", "modify_record",
])


@dataclass
class ConfidenceComponents:
    evidence_quality: float = 0.0     # [0,1]
    ml_support: float = 0.0           # [0,1]
    anomaly_agreement: float = 0.0    # [0,1]
    rule_match: float = 0.0           # [0,1]
    historical_match: float = 0.0     # [0,1]
    llm_signal: float = 0.5           # [0,1]  raw LLM confidence
    breakdown: dict = field(default_factory=dict)


def compute_evidence_quality(evidence: list[dict]) -> float:
    """Score evidence quality based on count and trust levels."""
    if not evidence:
        return 0.0
    total_weight = sum(
        _TRUST_WEIGHTS.get(str(e.get("trust_level", "SECONDARY")), 0.5)
        for e in evidence
    )
    # Scale: 5 high-trust docs = 1.0, diminishing returns
    raw = total_weight / max(len(evidence), 1)
    count_bonus = min(len(evidence) / 5.0, 1.0) * 0.3
    return min(raw * 0.7 + count_bonus, 1.0)


def compute_ml_support(ml_prediction: Optional[dict], root_cause: str) -> float:
    """Score how well ML prediction supports the determined root cause."""
    if not ml_prediction:
        return 0.5  # neutral
    predicted = ml_prediction.get("predicted_type", "")
    confidence = float(ml_prediction.get("confidence", 0.5))
    if predicted == root_cause:
        return confidence
    # Partial credit for related mismatches
    related_pairs = {
        ("FEE_VARIANCE", "AMOUNT_MISMATCH"),
        ("AMOUNT_MISMATCH", "FEE_VARIANCE"),
    }
    if (predicted, root_cause) in related_pairs:
        return confidence * 0.6
    return max(0.0, 0.5 - confidence * 0.3)


def compute_anomaly_agreement(anomaly_result: Optional[dict], root_cause: str) -> float:
    """Score anomaly signal alignment with root cause."""
    if not anomaly_result:
        return 0.5
    is_anomaly = anomaly_result.get("is_anomaly", False)
    score = float(anomaly_result.get("anomaly_score", 0.5))
    # UNKNOWN root cause with high anomaly → supports uncertainty
    if root_cause == "UNKNOWN":
        return 0.4
    # Most exceptions should show some anomaly signal
    if is_anomaly:
        return min(0.5 + score * 0.5, 1.0)
    # Low anomaly score for a real exception is somewhat concerning
    return max(0.3, 0.6 - score * 0.3)


def compute_rule_match(finance_rules: list[dict], root_cause: str) -> float:
    """Score whether retrieved finance rules support the root cause."""
    if not finance_rules:
        return 0.4  # no rule evidence → some penalty
    rule_text = " ".join(
        str(r.get("content", "")) + str(r.get("title", ""))
        for r in finance_rules
    ).lower()
    # Keyword mapping
    keywords = {
        "FEE_VARIANCE": ["fee", "processing", "deduction", "rate"],
        "AMOUNT_MISMATCH": ["mismatch", "amount", "difference", "discrepancy"],
        "DUPLICATE": ["duplicate", "same payment", "double"],
        "MISSING_INVOICE": ["invoice", "missing"],
        "MISSING_SETTLEMENT": ["settlement", "missing", "delay"],
        "REFUND_MISMATCH": ["refund", "reversal"],
        "DATE_MISMATCH": ["date", "timing", "delay", "window"],
    }
    kws = keywords.get(root_cause, [])
    if not kws:
        return 0.5
    hits = sum(1 for kw in kws if kw in rule_text)
    return min(hits / len(kws), 1.0)


def compute_historical_match(historical_cases: list[dict], root_cause: str) -> float:
    """Score how well similar historical cases match the current determination."""
    if not historical_cases:
        return 0.4
    rc_lower = root_cause.lower()
    matches = sum(
        1 for c in historical_cases
        if rc_lower in str(c.get("content", "") + str(c.get("title", ""))).lower()
    )
    return min(matches / max(len(historical_cases), 1), 1.0) * 0.8 + 0.2


def compute_confidence(
    evidence: list[dict],
    finance_rules: list[dict],
    historical_cases: list[dict],
    ml_prediction: Optional[dict],
    anomaly_result: Optional[dict],
    root_cause: str,
    llm_raw_confidence: float,
    contradiction_detected: bool,
) -> tuple[float, str, ConfidenceComponents]:
    """Compute final deterministic confidence score.

    Returns:
        (confidence: float, band: str, components: ConfidenceComponents)
    """
    components = ConfidenceComponents(
        evidence_quality=compute_evidence_quality(evidence),
        ml_support=compute_ml_support(ml_prediction, root_cause),
        anomaly_agreement=compute_anomaly_agreement(anomaly_result, root_cause),
        rule_match=compute_rule_match(finance_rules, root_cause),
        historical_match=compute_historical_match(historical_cases, root_cause),
        llm_signal=max(0.0, min(1.0, llm_raw_confidence)),
    )

    raw = (
        components.evidence_quality  * _WEIGHTS["evidence_quality"]
        + components.ml_support      * _WEIGHTS["ml_support"]
        + components.anomaly_agreement * _WEIGHTS["anomaly_agreement"]
        + components.rule_match      * _WEIGHTS["rule_match"]
        + components.historical_match * _WEIGHTS["historical_match"]
        + components.llm_signal      * _WEIGHTS["llm_signal"]
    )

    # Contradiction override — never allow HIGH confidence
    settings = get_settings()
    if contradiction_detected:
        raw = min(raw, settings.AI_CONFIDENCE_MEDIUM - 0.01)

    # UNKNOWN root cause is inherently uncertain
    if root_cause == "UNKNOWN":
        raw = min(raw, 0.65)

    confidence = round(max(0.0, min(1.0, raw)), 4)
    band = classify_band(confidence)

    components.breakdown = {
        "evidence_quality": round(components.evidence_quality, 3),
        "ml_support": round(components.ml_support, 3),
        "anomaly_agreement": round(components.anomaly_agreement, 3),
        "rule_match": round(components.rule_match, 3),
        "historical_match": round(components.historical_match, 3),
        "llm_signal": round(components.llm_signal, 3),
        "final": confidence,
        "band": band,
    }

    return confidence, band, components


def classify_band(confidence: float) -> str:
    """Classify confidence into HIGH / MEDIUM / LOW."""
    settings = get_settings()
    if confidence >= settings.AI_CONFIDENCE_HIGH:
        return "HIGH"
    if confidence >= settings.AI_CONFIDENCE_MEDIUM:
        return "MEDIUM"
    return "LOW"


def should_require_human_review(
    confidence: float,
    contradiction_detected: bool,
    root_cause: str,
    uncertainties: list[str],
) -> bool:
    """Determine if human review is required."""
    settings = get_settings()
    if contradiction_detected:
        return True
    if confidence < settings.AI_CONFIDENCE_MEDIUM:
        return True
    if root_cause == "UNKNOWN":
        return True
    if len(uncertainties) >= 2:
        return True
    return False


def detect_contradiction(
    evidence: list[dict],
    ml_prediction: Optional[dict],
    root_cause: str,
    findings: list[str],
) -> tuple[bool, list[str]]:
    """Check for contradictions between evidence signals.

    Returns (contradiction_detected, list_of_contradiction_messages)
    """
    contradictions = []

    # Check ML vs determined root cause
    if ml_prediction:
        ml_type = ml_prediction.get("predicted_type", "")
        ml_conf = float(ml_prediction.get("confidence", 0))
        related = {
            ("FEE_VARIANCE", "AMOUNT_MISMATCH"),
            ("AMOUNT_MISMATCH", "FEE_VARIANCE"),
        }
        if (
            ml_type
            and ml_type != root_cause
            and (ml_type, root_cause) not in related
            and ml_conf > 0.70
        ):
            contradictions.append(
                f"ML classifier predicted {ml_type} (confidence {ml_conf:.0%}) "
                f"but investigation determined {root_cause}."
            )

    # Check for explicit contradictions in findings
    contradiction_keywords = ["contradict", "mismatch with", "inconsistent", "does not match"]
    for finding in findings:
        if any(kw in finding.lower() for kw in contradiction_keywords):
            contradictions.append(f"Finding indicates contradiction: {finding[:120]}")

    return bool(contradictions), contradictions


def is_safe_action(action: str) -> bool:
    """Return True only if the action is safe (read-only).

    Phase 3B enforces a read-only boundary. Any write action is rejected.
    """
    return action.lower() not in SAFETY_BOUNDARY_ACTIONS
