"""Rollback support for reversible actions.

Only actions explicitly marked as reversible in the action registry
can be rolled back. Not all actions are reversible.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.controller.action_registry import get_action_metadata
from app.models.audit_log import AuditAction
from app.models.controller import ActionResult, ActionStatus
from app.models.exception import Exception as FinancialException, ExceptionStatus
from app.services.audit_service import AuditService

logger = logging.getLogger(__name__)


class RollbackError(Exception):
    pass


# Map of actions to their rollback target states
_ROLLBACK_MAP = {
    "MARK_EXCEPTION_RESOLVED": ExceptionStatus.IN_REVIEW,
    "MARK_EXCEPTION_REVIEWED": ExceptionStatus.OPEN,
    "APPLY_FEE_VARIANCE_RECONCILIATION": ExceptionStatus.IN_REVIEW,
}


def rollback_action(
    db: Session,
    action_result_id: uuid.UUID,
    user_id: Optional[uuid.UUID] = None,
    merchant_id: Optional[uuid.UUID] = None,
) -> ActionResult:
    """Rollback a previously executed action.

    Only works for actions marked as reversible in the action registry.
    """
    result = db.get(ActionResult, action_result_id)
    if not result:
        raise RollbackError(f"Action result {action_result_id} not found")

    if result.rolled_back:
        raise RollbackError("Action has already been rolled back")

    if result.status != ActionStatus.SUCCESS:
        raise RollbackError(f"Cannot rollback action with status {result.status}")

    meta = get_action_metadata(result.action)
    if meta is None or not meta.reversible:
        raise RollbackError(f"Action '{result.action}' is not reversible")

    target_status = _ROLLBACK_MAP.get(result.action)
    if target_status is None:
        raise RollbackError(f"No rollback mapping for action '{result.action}'")

    # Load and lock exception
    exception = (
        db.query(FinancialException)
        .filter(FinancialException.id == result.exception_id)
        .with_for_update()
        .first()
    )
    if not exception:
        raise RollbackError(f"Exception {result.exception_id} not found")

    previous_state = exception.status.value
    exception.status = target_status

    result.rolled_back = True
    result.rolled_back_at = datetime.now(timezone.utc)
    result.status = ActionStatus.ROLLED_BACK

    db.commit()
    db.refresh(result)

    AuditService(db).log(
        AuditAction.ACTION_ROLLED_BACK,
        f"Action {result.action} rolled back: {previous_state} → {target_status.value}",
        user_id=user_id,
        merchant_id=merchant_id,
        entity_type="exception",
        entity_id=str(result.exception_id),
        metadata={
            "action_result_id": str(result.id),
            "action": result.action,
            "previous_state": previous_state,
            "rollback_state": target_status.value,
        },
    )

    logger.info(
        "Rolled back action %s on exception %s: %s → %s",
        result.action, result.exception_id, previous_state, target_status.value,
    )
    return result
