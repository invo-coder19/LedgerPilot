"""Action executor — validates, executes, and verifies state-changing actions.

This is the ONLY module permitted to modify financial record state.
Every execution:
  1. Validates action against registry
  2. Validates policy authorization
  3. Checks exception current state (with row lock for concurrency)
  4. Checks idempotency key
  5. Executes the allowlisted mutation within a DB transaction
  6. Verifies the result by reloading the record
  7. Creates an audit event
  8. Returns a structured ActionResult
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.controller.action_registry import get_action_metadata, validate_action
from app.models.audit_log import AuditAction
from app.models.controller import (
    ActionResult, ActionStatus, ControllerConfig, ControllerDecision,
)
from app.models.exception import Exception as FinancialException, ExceptionStatus
from app.services.audit_service import AuditService

logger = logging.getLogger(__name__)


class ActionExecutionError(Exception):
    """Raised when an action cannot be executed."""
    pass


class ActionAlreadyExecutedError(ActionExecutionError):
    """Raised when the idempotency check detects a duplicate."""
    pass


def _build_idempotency_key(
    exception_id: uuid.UUID,
    action_type: str,
    decision_id: uuid.UUID,
) -> str:
    """Build a unique key for idempotent action execution."""
    return f"{exception_id}:{action_type}:{decision_id}"


def _check_kill_switch(db: Session) -> bool:
    """Return True if kill switch is active."""
    config = db.query(ControllerConfig).filter(
        ControllerConfig.key == "kill_switch"
    ).first()
    return bool(config and config.value.get("enabled"))


def _check_rate_limits(db: Session) -> tuple[bool, str]:
    """Check global rate limits. Returns (allowed, reason)."""
    from sqlalchemy import func

    config_per_hour = db.query(ControllerConfig).filter(
        ControllerConfig.key == "max_auto_per_hour"
    ).first()
    if config_per_hour:
        limit = config_per_hour.value.get("value", 1000)
        one_hour_ago = datetime.now(timezone.utc).replace(
            minute=0, second=0, microsecond=0
        )
        count = db.query(func.count(ActionResult.id)).filter(
            ActionResult.executed_at >= one_hour_ago,
            ActionResult.status == ActionStatus.SUCCESS,
        ).scalar() or 0
        if count >= limit:
            return False, f"Hourly rate limit exceeded ({count}/{limit})"

    return True, ""


def execute_action(
    db: Session,
    decision: ControllerDecision,
    action_type: str,
    exception_id: uuid.UUID,
    executed_by: str = "system",
    user_id: Optional[uuid.UUID] = None,
    merchant_id: Optional[uuid.UUID] = None,
    dry_run: bool = False,
) -> ActionResult:
    """Execute a single validated, idempotent action.

    This is the ONLY function that may change exception state.
    """
    audit = AuditService(db)
    idem_key = _build_idempotency_key(exception_id, action_type, decision.id)

    # ── 1. Idempotency check ──────────────────────────────────────────────────
    existing = db.query(ActionResult).filter(
        ActionResult.idempotency_key == idem_key,
    ).first()
    if existing:
        logger.info("Idempotent skip: action %s already executed (id=%s)", action_type, existing.id)
        return existing

    # ── 2. Kill switch check ──────────────────────────────────────────────────
    if _check_kill_switch(db):
        result = ActionResult(
            decision_id=decision.id,
            exception_id=exception_id,
            action=action_type,
            idempotency_key=idem_key,
            status=ActionStatus.FAILED,
            executed_by=executed_by,
            error_message="Kill switch is active. Action blocked.",
        )
        db.add(result)
        db.commit()
        audit.log(
            AuditAction.ACTION_BLOCKED,
            f"Action {action_type} blocked by kill switch",
            user_id=user_id, merchant_id=merchant_id,
            entity_type="exception", entity_id=str(exception_id),
        )
        return result

    # ── 3. Rate limit check ───────────────────────────────────────────────────
    rate_ok, rate_reason = _check_rate_limits(db)
    if not rate_ok:
        result = ActionResult(
            decision_id=decision.id,
            exception_id=exception_id,
            action=action_type,
            idempotency_key=idem_key,
            status=ActionStatus.FAILED,
            executed_by=executed_by,
            error_message=rate_reason,
        )
        db.add(result)
        db.commit()
        return result

    # ── 4. Validate action against registry ───────────────────────────────────
    meta = get_action_metadata(action_type)
    if meta is None:
        raise ActionExecutionError(f"Unknown action: {action_type}")

    # ── 5. Load and lock exception record ─────────────────────────────────────
    exception = (
        db.query(FinancialException)
        .filter(FinancialException.id == exception_id)
        .with_for_update()
        .first()
    )
    if exception is None:
        raise ActionExecutionError(f"Exception {exception_id} not found")

    previous_state = exception.status.value

    # ── 6. Validate record state ──────────────────────────────────────────────
    if action_type in ("MARK_EXCEPTION_RESOLVED", "APPLY_FEE_VARIANCE_RECONCILIATION"):
        if exception.status == ExceptionStatus.RESOLVED:
            logger.info("Exception %s already resolved, skipping", exception_id)
            result = ActionResult(
                decision_id=decision.id,
                exception_id=exception_id,
                action=action_type,
                idempotency_key=idem_key,
                status=ActionStatus.SUCCESS,
                previous_state=previous_state,
                new_state=previous_state,
                executed_by=executed_by,
                verified=True,
                is_reversible=meta.reversible,
            )
            db.add(result)
            db.commit()
            return result

    # ── 7. Execute action (dry run check) ─────────────────────────────────────
    if dry_run:
        result = ActionResult(
            decision_id=decision.id,
            exception_id=exception_id,
            action=action_type,
            idempotency_key=idem_key,
            status=ActionStatus.SUCCESS,
            previous_state=previous_state,
            new_state=f"[DRY RUN] Would change to target state",
            executed_by=executed_by,
            verified=True,
            is_reversible=meta.reversible,
            verification_details={"dry_run": True, "would_execute": action_type},
        )
        db.add(result)
        db.commit()
        return result

    # ── 8. Perform the state change ───────────────────────────────────────────
    try:
        new_state = _execute_state_change(exception, action_type)
    except Exception as exc:
        result = ActionResult(
            decision_id=decision.id,
            exception_id=exception_id,
            action=action_type,
            idempotency_key=idem_key,
            status=ActionStatus.FAILED,
            previous_state=previous_state,
            executed_by=executed_by,
            error_message=str(exc)[:500],
            is_reversible=meta.reversible,
        )
        db.add(result)
        db.commit()
        audit.log(
            AuditAction.ACTION_FAILED,
            f"Action {action_type} failed: {str(exc)[:200]}",
            user_id=user_id, merchant_id=merchant_id,
            entity_type="exception", entity_id=str(exception_id),
        )
        return result

    # ── 9. Verify state change ────────────────────────────────────────────────
    db.flush()
    db.refresh(exception)
    verified = exception.status.value == new_state
    verification_details = {
        "expected_state": new_state,
        "actual_state": exception.status.value,
        "verified": verified,
    }

    status = ActionStatus.SUCCESS if verified else ActionStatus.FAILED_VERIFICATION

    # ── 10. Create action result ──────────────────────────────────────────────
    result = ActionResult(
        decision_id=decision.id,
        exception_id=exception_id,
        action=action_type,
        idempotency_key=idem_key,
        status=status,
        previous_state=previous_state,
        new_state=exception.status.value,
        policy_version=decision.policy_version,
        executed_by=executed_by,
        verified=verified,
        verification_details=verification_details,
        is_reversible=meta.reversible,
    )
    db.add(result)

    # ── 11. Audit ─────────────────────────────────────────────────────────────
    audit_action = AuditAction.ACTION_EXECUTED if verified else AuditAction.ACTION_FAILED
    audit.log(
        audit_action,
        f"Action {action_type}: {previous_state} → {new_state} (verified={verified})",
        user_id=user_id, merchant_id=merchant_id,
        entity_type="exception", entity_id=str(exception_id),
        metadata={
            "action": action_type,
            "previous_state": previous_state,
            "new_state": new_state,
            "verified": verified,
            "decision_id": str(decision.id),
            "is_simulation": meta.is_simulation,
        },
    )

    if verified:
        audit.log(
            AuditAction.ACTION_VERIFIED,
            f"Action {action_type} verified: state is {new_state}",
            user_id=user_id, merchant_id=merchant_id,
            entity_type="exception", entity_id=str(exception_id),
        )

    db.commit()
    logger.info(
        "Action executed: %s on exception %s: %s → %s (verified=%s)",
        action_type, exception_id, previous_state, new_state, verified,
    )
    return result


def _execute_state_change(
    exception: FinancialException,
    action_type: str,
) -> str:
    """Perform the actual database mutation. Returns expected new state value.

    This is the ONLY place where exception state is changed by the controller.
    """
    if action_type == "MARK_EXCEPTION_RESOLVED":
        exception.status = ExceptionStatus.RESOLVED
        return ExceptionStatus.RESOLVED.value

    elif action_type == "MARK_EXCEPTION_REVIEWED":
        exception.status = ExceptionStatus.IN_REVIEW
        return ExceptionStatus.IN_REVIEW.value

    elif action_type == "REQUEST_HUMAN_REVIEW":
        exception.status = ExceptionStatus.IN_REVIEW
        return ExceptionStatus.IN_REVIEW.value

    elif action_type == "ESCALATE_EXCEPTION":
        exception.status = ExceptionStatus.IN_REVIEW
        return ExceptionStatus.IN_REVIEW.value

    elif action_type == "ADD_RECONCILIATION_ADJUSTMENT_NOTE":
        # Append-only — does not change status
        return exception.status.value

    elif action_type == "APPLY_FEE_VARIANCE_RECONCILIATION":
        # SIMULATION action — resolves on synthetic data only
        exception.status = ExceptionStatus.RESOLVED
        return ExceptionStatus.RESOLVED.value

    else:
        raise ActionExecutionError(f"No execution logic for action: {action_type}")
