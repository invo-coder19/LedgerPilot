"""Stopping rules — explicit conditions that halt the controller.

If any stopping rule fires, the controller MUST NOT execute the action.
Instead it returns a BLOCK or ESCALATE decision.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.models.controller import RiskBand


@dataclass
class StopReason:
    """Describes why the controller stopped."""
    rule: str
    reason: str
    severity: str  # WARNING | CRITICAL


def check_stopping_rules(
    confidence: float,
    risk_score: float,
    risk_band: RiskBand,
    contradiction_detected: bool,
    evidence_count: int,
    exception_type: str,
    root_cause: str,
) -> Optional[StopReason]:
    """Evaluate all stopping rules in priority order.

    Returns the first matching StopReason, or None if all rules pass.
    """

    # 1. Critical risk → always stop
    if risk_band == RiskBand.CRITICAL:
        return StopReason(
            rule="critical_risk",
            reason=f"Risk band is CRITICAL (score={risk_score:.4f}). Autonomous action not permitted.",
            severity="CRITICAL",
        )

    # 2. Evidence contradictions → stop
    if contradiction_detected:
        return StopReason(
            rule="contradictory_evidence",
            reason="Evidence contradictions detected. Human review required.",
            severity="CRITICAL",
        )

    # 3. Confidence too low → stop
    if confidence < 0.50:
        return StopReason(
            rule="low_confidence",
            reason=f"Confidence {confidence:.0%} is below minimum threshold (50%). Cannot safely act.",
            severity="CRITICAL",
        )

    # 4. No evidence available → stop
    if evidence_count == 0:
        return StopReason(
            rule="no_evidence",
            reason="No evidence available. Required evidence is missing.",
            severity="CRITICAL",
        )

    # 5. UNKNOWN root cause → stop auto-execution
    if root_cause == "UNKNOWN":
        return StopReason(
            rule="unknown_root_cause",
            reason="Root cause could not be determined. Human review required.",
            severity="WARNING",
        )

    # 6. High risk → escalate
    if risk_band == RiskBand.HIGH:
        return StopReason(
            rule="high_risk",
            reason=f"Risk band is HIGH (score={risk_score:.4f}). Escalating to human review.",
            severity="WARNING",
        )

    # All rules passed
    return None
