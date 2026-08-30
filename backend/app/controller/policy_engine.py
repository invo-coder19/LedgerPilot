"""Centralized policy engine.

The policy engine evaluates whether a requested action is permitted,
what level of approval is required, and which specific policy governs
the decision.

The LLM CANNOT override this engine.  All decisions are deterministic.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from sqlalchemy.orm import Session

from app.models.controller import (
    ControllerConfig, ControllerPolicy, PolicyStatus, RiskBand,
)

logger = logging.getLogger(__name__)


@dataclass
class PolicyResult:
    """Output of policy evaluation."""
    allowed: bool
    decision: str          # AUTO_EXECUTE | RECOMMEND | ESCALATE | BLOCK
    required_approval_level: str  # NONE | FINANCE_MANAGER | ADMIN
    reason: str
    policy_version: str
    policy_name: str


# ── Default built-in policy configurations ────────────────────────────────────

DEFAULT_POLICIES = {
    "fee_variance_auto_resolve": {
        "name": "Fee Variance Auto-Resolution",
        "description": "Allows automatic resolution of fee variance exceptions when confidence is high, amount is small, and no evidence conflict exists.",
        "configuration": {
            "exception_types": ["AMOUNT_MISMATCH"],
            "root_causes": ["FEE_VARIANCE"],
            "confidence_threshold": 0.95,
            "max_amount": 10000.0,
            "max_risk_band": "LOW",
            "requires_evidence_conflict_check": True,
            "allowed_actions": ["MARK_EXCEPTION_RESOLVED", "APPLY_FEE_VARIANCE_RECONCILIATION"],
        },
    },
    "duplicate_high_value": {
        "name": "Duplicate High-Value Review",
        "description": "Never auto-resolve high-value duplicate exceptions. Always require human approval above the configured threshold.",
        "configuration": {
            "exception_types": ["DUPLICATE"],
            "root_causes": ["DUPLICATE"],
            "confidence_threshold": 0.90,
            "max_amount_auto": 5000.0,
            "human_review_threshold": 5000.0,
            "max_risk_band": "MEDIUM",
            "allowed_actions": ["MARK_EXCEPTION_RESOLVED", "MARK_EXCEPTION_REVIEWED"],
        },
    },
    "unknown_transaction": {
        "name": "Unknown Transaction Escalation",
        "description": "Unknown transactions can never be auto-resolved. Always escalate.",
        "configuration": {
            "exception_types": ["UNKNOWN"],
            "root_causes": ["UNKNOWN"],
            "always_escalate": True,
            "allowed_actions": ["ESCALATE_EXCEPTION", "REQUEST_HUMAN_REVIEW"],
        },
    },
    "large_discrepancy": {
        "name": "Large Discrepancy Human Review",
        "description": "All discrepancies above a financial threshold require human review regardless of confidence.",
        "configuration": {
            "exception_types": ["AMOUNT_MISMATCH", "MISSING_SETTLEMENT", "MISSING_INVOICE", "REFUND_MISMATCH"],
            "root_causes": ["AMOUNT_MISMATCH", "MISSING_SETTLEMENT", "MISSING_INVOICE", "REFUND_MISMATCH"],
            "human_review_amount_threshold": 50000.0,
            "confidence_threshold": 0.70,
            "allowed_actions": ["MARK_EXCEPTION_RESOLVED", "MARK_EXCEPTION_REVIEWED", "REQUEST_HUMAN_REVIEW"],
        },
    },
}


def _get_kill_switch(db: Session) -> bool:
    """Check if the kill switch is active."""
    config = db.query(ControllerConfig).filter(
        ControllerConfig.key == "kill_switch"
    ).first()
    if config and config.value.get("enabled"):
        return True
    return False


def _get_active_policies(db: Session) -> list[ControllerPolicy]:
    """Load all active policies from the database."""
    return (
        db.query(ControllerPolicy)
        .filter(ControllerPolicy.status == PolicyStatus.ACTIVE)
        .all()
    )


def _find_matching_policy(
    policies: list[ControllerPolicy],
    exception_type: str,
    root_cause: str,
) -> Optional[ControllerPolicy]:
    """Find the most specific active policy matching the exception."""
    best = None
    for pol in policies:
        cfg = pol.configuration
        exc_types = cfg.get("exception_types", [])
        root_causes = cfg.get("root_causes", [])
        # Match by root cause first, then exception type
        if root_cause in root_causes or exception_type in exc_types:
            if best is None:
                best = pol
            elif root_cause in root_causes:
                best = pol  # more specific match
    return best


def evaluate(
    db: Session,
    exception_type: str,
    root_cause: str,
    confidence: float,
    risk_score: float,
    risk_band: RiskBand,
    amount: Optional[float],
    contradiction_detected: bool,
    requested_action: str,
) -> PolicyResult:
    """Evaluate a proposed action against all active policies.

    This is the single entry point for policy evaluation.
    The LLM cannot bypass or override this function.
    """
    # ── Kill switch check ─────────────────────────────────────────────────────
    if _get_kill_switch(db):
        return PolicyResult(
            allowed=False,
            decision="BLOCK",
            required_approval_level="ADMIN",
            reason="Controller kill switch is active. All autonomous actions are blocked.",
            policy_version="kill_switch",
            policy_name="Kill Switch",
        )

    # ── Load policies ─────────────────────────────────────────────────────────
    policies = _get_active_policies(db)
    policy = _find_matching_policy(policies, exception_type, root_cause)

    if policy is None:
        # No matching policy → cannot auto-execute, recommend human review
        return PolicyResult(
            allowed=False,
            decision="ESCALATE",
            required_approval_level="FINANCE_MANAGER",
            reason=f"No active policy found for exception_type={exception_type} root_cause={root_cause}. Escalating to human review.",
            policy_version="none",
            policy_name="Default Escalation",
        )

    cfg = policy.configuration
    policy_ver = f"{policy.policy_id}_v{policy.version}"

    # ── Always-escalate check ─────────────────────────────────────────────────
    if cfg.get("always_escalate"):
        return PolicyResult(
            allowed=False,
            decision="ESCALATE",
            required_approval_level="FINANCE_MANAGER",
            reason=f"Policy '{policy.name}' requires mandatory escalation for {exception_type}/{root_cause}.",
            policy_version=policy_ver,
            policy_name=policy.name,
        )

    # ── Validate action is in policy's allowed list ───────────────────────────
    allowed_actions = cfg.get("allowed_actions", [])
    if requested_action and requested_action not in allowed_actions:
        return PolicyResult(
            allowed=False,
            decision="BLOCK",
            required_approval_level="ADMIN",
            reason=f"Action '{requested_action}' is not permitted by policy '{policy.name}'. Allowed: {allowed_actions}.",
            policy_version=policy_ver,
            policy_name=policy.name,
        )

    # ── Evidence conflict ─────────────────────────────────────────────────────
    if cfg.get("requires_evidence_conflict_check") and contradiction_detected:
        return PolicyResult(
            allowed=False,
            decision="BLOCK",
            required_approval_level="FINANCE_MANAGER",
            reason=f"Evidence conflict detected. Policy '{policy.name}' blocks automatic action when contradictions exist.",
            policy_version=policy_ver,
            policy_name=policy.name,
        )

    # ── Risk band check ───────────────────────────────────────────────────────
    max_risk = cfg.get("max_risk_band", "LOW")
    risk_order = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}
    if risk_order.get(risk_band.value, 3) > risk_order.get(max_risk, 0):
        if risk_band in (RiskBand.HIGH, RiskBand.CRITICAL):
            return PolicyResult(
                allowed=False,
                decision="ESCALATE",
                required_approval_level="FINANCE_MANAGER",
                reason=f"Risk band {risk_band.value} exceeds policy maximum {max_risk}.",
                policy_version=policy_ver,
                policy_name=policy.name,
            )
        return PolicyResult(
            allowed=True,
            decision="RECOMMEND",
            required_approval_level="FINANCE_MANAGER",
            reason=f"Risk band {risk_band.value} exceeds auto-execution maximum {max_risk}. Recommending for human review.",
            policy_version=policy_ver,
            policy_name=policy.name,
        )

    # ── Amount threshold for human review ─────────────────────────────────────
    human_review_threshold = cfg.get("human_review_amount_threshold") or cfg.get("human_review_threshold")
    if human_review_threshold and amount and float(amount) > human_review_threshold:
        return PolicyResult(
            allowed=True,
            decision="RECOMMEND",
            required_approval_level="FINANCE_MANAGER",
            reason=f"Amount ₹{amount:,.2f} exceeds human review threshold ₹{human_review_threshold:,.2f}.",
            policy_version=policy_ver,
            policy_name=policy.name,
        )

    # ── Confidence check ──────────────────────────────────────────────────────
    min_confidence = cfg.get("confidence_threshold", 0.95)
    if confidence < min_confidence:
        if confidence < 0.50:
            return PolicyResult(
                allowed=False,
                decision="ESCALATE",
                required_approval_level="FINANCE_MANAGER",
                reason=f"Confidence {confidence:.0%} is below minimum. Escalating.",
                policy_version=policy_ver,
                policy_name=policy.name,
            )
        return PolicyResult(
            allowed=True,
            decision="RECOMMEND",
            required_approval_level="FINANCE_MANAGER",
            reason=f"Confidence {confidence:.0%} is below auto-execution threshold {min_confidence:.0%}. Recommending for review.",
            policy_version=policy_ver,
            policy_name=policy.name,
        )

    # ── Auto-execution amount limit ───────────────────────────────────────────
    max_auto_amount = cfg.get("max_amount") or cfg.get("max_amount_auto")
    if max_auto_amount and amount and float(amount) > max_auto_amount:
        return PolicyResult(
            allowed=True,
            decision="RECOMMEND",
            required_approval_level="FINANCE_MANAGER",
            reason=f"Amount ₹{amount:,.2f} exceeds auto-execution limit ₹{max_auto_amount:,.2f}. Recommending for approval.",
            policy_version=policy_ver,
            policy_name=policy.name,
        )

    # ── All checks passed — auto-execute ──────────────────────────────────────
    return PolicyResult(
        allowed=True,
        decision="AUTO_EXECUTE",
        required_approval_level="NONE",
        reason=f"Policy '{policy.name}' allows auto-execution: confidence={confidence:.0%}, risk={risk_band.value}, amount={'₹{:,.2f}'.format(amount) if amount else 'N/A'}.",
        policy_version=policy_ver,
        policy_name=policy.name,
    )
