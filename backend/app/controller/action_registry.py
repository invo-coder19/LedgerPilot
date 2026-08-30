"""Explicit action registry — allowlist of all permitted state-changing actions.

No action may execute unless it is registered here.
Unknown actions are always rejected.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ActionMetadata:
    """Metadata describing a registered action."""
    action_type: str
    description: str
    allowed: bool
    required_role: str       # "system" | "FINANCE_MANAGER" | "ADMIN"
    max_amount: Optional[float]  # None = no limit
    max_risk_band: str       # LOW | MEDIUM | HIGH
    reversible: bool
    is_simulation: bool = False


# ── Registry ──────────────────────────────────────────────────────────────────

_REGISTRY: dict[str, ActionMetadata] = {
    "MARK_EXCEPTION_RESOLVED": ActionMetadata(
        action_type="MARK_EXCEPTION_RESOLVED",
        description="Mark a financial exception as resolved.",
        allowed=True,
        required_role="system",
        max_amount=None,  # Controlled by policy
        max_risk_band="LOW",
        reversible=True,
    ),
    "MARK_EXCEPTION_REVIEWED": ActionMetadata(
        action_type="MARK_EXCEPTION_REVIEWED",
        description="Mark exception as reviewed (IN_REVIEW status).",
        allowed=True,
        required_role="system",
        max_amount=None,
        max_risk_band="MEDIUM",
        reversible=True,
    ),
    "ADD_RECONCILIATION_ADJUSTMENT_NOTE": ActionMetadata(
        action_type="ADD_RECONCILIATION_ADJUSTMENT_NOTE",
        description="Add an adjustment note to an exception (append-only).",
        allowed=True,
        required_role="system",
        max_amount=None,
        max_risk_band="HIGH",
        reversible=False,
    ),
    "REQUEST_HUMAN_REVIEW": ActionMetadata(
        action_type="REQUEST_HUMAN_REVIEW",
        description="Request human review of the exception.",
        allowed=True,
        required_role="system",
        max_amount=None,
        max_risk_band="CRITICAL",
        reversible=False,
    ),
    "ESCALATE_EXCEPTION": ActionMetadata(
        action_type="ESCALATE_EXCEPTION",
        description="Escalate the exception for senior review.",
        allowed=True,
        required_role="system",
        max_amount=None,
        max_risk_band="CRITICAL",
        reversible=False,
    ),
    "APPLY_FEE_VARIANCE_RECONCILIATION": ActionMetadata(
        action_type="APPLY_FEE_VARIANCE_RECONCILIATION",
        description="[SIMULATION] Apply fee variance reconciliation adjustment. "
                    "This is a DEMO action on synthetic data — NO real money movement.",
        allowed=True,
        required_role="system",
        max_amount=10000.0,
        max_risk_band="LOW",
        reversible=True,
        is_simulation=True,
    ),
}


def get_action_metadata(action_type: str) -> Optional[ActionMetadata]:
    """Return metadata for a registered action, or None if unknown."""
    return _REGISTRY.get(action_type)


def is_action_registered(action_type: str) -> bool:
    """Check whether an action is registered."""
    return action_type in _REGISTRY


def is_action_allowed(action_type: str) -> bool:
    """Check whether a registered action is currently allowed."""
    meta = _REGISTRY.get(action_type)
    return meta is not None and meta.allowed


def list_actions() -> list[ActionMetadata]:
    """Return all registered actions."""
    return list(_REGISTRY.values())


def validate_action(
    action_type: str,
    amount: Optional[float] = None,
    risk_band: str = "LOW",
) -> tuple[bool, str]:
    """Validate an action against the registry.

    Returns (is_valid, reason).
    """
    meta = _REGISTRY.get(action_type)
    if meta is None:
        return False, f"Action '{action_type}' is not registered. Unknown actions are always rejected."
    if not meta.allowed:
        return False, f"Action '{action_type}' is currently disabled."
    if meta.max_amount is not None and amount is not None and amount > meta.max_amount:
        return False, f"Amount {amount} exceeds action maximum {meta.max_amount}."
    risk_order = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}
    if risk_order.get(risk_band, 3) > risk_order.get(meta.max_risk_band, 0):
        return False, f"Risk band {risk_band} exceeds action maximum {meta.max_risk_band}."
    return True, "Action validated."
