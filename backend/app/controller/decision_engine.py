"""Decision engine — combines confidence gates + risk gating + policy evaluation.

This is the routing layer that turns an investigation result into a
ControllerDecision of type AUTO_EXECUTE | RECOMMEND | ESCALATE | BLOCK.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from app.controller import policy_engine, risk_engine
from app.controller.action_registry import get_action_metadata, is_action_registered
from app.controller.stopping_rules import check_stopping_rules, StopReason
from app.models.controller import RiskBand

logger = logging.getLogger(__name__)


@dataclass
class DecisionResult:
    """Output of the decision engine."""
    decision: str          # AUTO_EXECUTE | RECOMMEND | ESCALATE | BLOCK
    action: Optional[str]  # proposed action type
    confidence: float
    risk_score: float
    risk_band: RiskBand
    reason: str
    evidence_ids: list[str]
    requires_human_approval: bool
    policy_version: str
    policy_name: str
    risk_details: dict
    stop_reason: Optional[str] = None


def _select_action(
    root_cause: str,
    exception_type: str,
    risk_band: RiskBand,
) -> Optional[str]:
    """Select the most appropriate action for the exception."""
    # Map root causes / exception types to default actions
    action_map = {
        "FEE_VARIANCE": "MARK_EXCEPTION_RESOLVED",
        "AMOUNT_MISMATCH": "MARK_EXCEPTION_RESOLVED",
        "DUPLICATE": "MARK_EXCEPTION_REVIEWED",
        "MISSING_INVOICE": "REQUEST_HUMAN_REVIEW",
        "MISSING_SETTLEMENT": "REQUEST_HUMAN_REVIEW",
        "REFUND_MISMATCH": "MARK_EXCEPTION_REVIEWED",
        "DATE_MISMATCH": "MARK_EXCEPTION_RESOLVED",
        "UNKNOWN": "ESCALATE_EXCEPTION",
    }
    action = action_map.get(root_cause)
    if action and is_action_registered(action):
        return action
    # Fallback based on risk
    if risk_band == RiskBand.CRITICAL:
        return "ESCALATE_EXCEPTION"
    if risk_band in (RiskBand.HIGH, RiskBand.MEDIUM):
        return "REQUEST_HUMAN_REVIEW"
    return "MARK_EXCEPTION_REVIEWED"


def make_decision(
    db: Session,
    exception_type: str,
    root_cause: str,
    confidence: float,
    amount: Optional[Decimal],
    evidence_count: int,
    avg_trust: float,
    has_primary_evidence: bool,
    contradiction_detected: bool,
    uncertainty_count: int,
    requires_human: bool,
    ml_confidence: Optional[float],
    ml_agrees_with_ai: bool,
    evidence_ids: list[str],
) -> DecisionResult:
    """Run the full decision pipeline: risk → stopping → action → policy.

    This function is the single deterministic entry point for Phase 4 decisions.
    """
    # ── Step 1: Risk Assessment ───────────────────────────────────────────────
    risk = risk_engine.assess_risk(
        amount=amount,
        evidence_count=evidence_count,
        avg_trust=avg_trust,
        has_primary_evidence=has_primary_evidence,
        contradiction_detected=contradiction_detected,
        uncertainty_count=uncertainty_count,
        requires_human=requires_human,
        exception_type=exception_type,
        ml_confidence=ml_confidence,
        ai_confidence=confidence,
        ml_agrees_with_ai=ml_agrees_with_ai,
    )

    # ── Step 2: Stopping Rules ────────────────────────────────────────────────
    stop = check_stopping_rules(
        confidence=confidence,
        risk_score=risk.risk_score,
        risk_band=risk.risk_band,
        contradiction_detected=contradiction_detected,
        evidence_count=evidence_count,
        exception_type=exception_type,
        root_cause=root_cause,
    )

    if stop:
        decision_type = "BLOCK" if stop.severity == "CRITICAL" else "ESCALATE"
        return DecisionResult(
            decision=decision_type,
            action="ESCALATE_EXCEPTION" if decision_type == "ESCALATE" else None,
            confidence=confidence,
            risk_score=risk.risk_score,
            risk_band=risk.risk_band,
            reason=f"Controller stopped: {stop.reason}",
            evidence_ids=evidence_ids,
            requires_human_approval=True,
            policy_version="stopping_rule",
            policy_name="Stopping Rule",
            risk_details=risk.details,
            stop_reason=stop.reason,
        )

    # ── Step 3: Select Action ─────────────────────────────────────────────────
    proposed_action = _select_action(root_cause, exception_type, risk.risk_band)

    # ── Step 4: Policy Evaluation ─────────────────────────────────────────────
    policy_result = policy_engine.evaluate(
        db=db,
        exception_type=exception_type,
        root_cause=root_cause,
        confidence=confidence,
        risk_score=risk.risk_score,
        risk_band=risk.risk_band,
        amount=float(amount) if amount else None,
        contradiction_detected=contradiction_detected,
        requested_action=proposed_action or "",
    )

    # ── Step 5: Map policy decision ───────────────────────────────────────────
    decision_type = policy_result.decision
    requires_approval = decision_type in ("RECOMMEND", "ESCALATE")

    if decision_type == "BLOCK":
        proposed_action = None

    logger.info(
        "Decision: %s action=%s confidence=%.2f risk=%.4f/%s policy=%s",
        decision_type, proposed_action, confidence,
        risk.risk_score, risk.risk_band.value, policy_result.policy_version,
    )

    return DecisionResult(
        decision=decision_type,
        action=proposed_action,
        confidence=confidence,
        risk_score=risk.risk_score,
        risk_band=risk.risk_band,
        reason=policy_result.reason,
        evidence_ids=evidence_ids,
        requires_human_approval=requires_approval,
        policy_version=policy_result.policy_version,
        policy_name=policy_result.policy_name,
        risk_details=risk.details,
    )
