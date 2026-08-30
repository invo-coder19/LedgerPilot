"""Human approval service — manages the approval/rejection lifecycle."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.controller.action_executor import execute_action
from app.models.audit_log import AuditAction
from app.models.controller import (
    ApprovalRequest, ApprovalStatus,
    ControllerDecision, ControllerDecisionStatus,
    ActionResult,
)
from app.models.user import Role
from app.services.audit_service import AuditService

logger = logging.getLogger(__name__)

# Approval expiry: 72 hours
APPROVAL_EXPIRY_HOURS = 72

# Roles that can approve
APPROVAL_ROLES = {Role.FINANCE_MANAGER, Role.ADMIN}
# Roles that can reject
REJECTION_ROLES = {Role.FINANCE_MANAGER, Role.ADMIN}


def create_approval_request(
    db: Session,
    decision: ControllerDecision,
    merchant_id: Optional[uuid.UUID] = None,
) -> ApprovalRequest:
    """Create an approval request from a RECOMMEND decision."""
    from app.models.exception import Exception as FinancialException

    exception = db.get(FinancialException, decision.exception_id)
    amount = exception.amount if exception else None

    approval = ApprovalRequest(
        exception_id=decision.exception_id,
        decision_id=decision.id,
        requested_action=decision.action or "MARK_EXCEPTION_REVIEWED",
        amount=amount,
        risk_score=decision.risk_score,
        confidence=decision.confidence,
        reason=decision.reason,
        status=ApprovalStatus.PENDING,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=APPROVAL_EXPIRY_HOURS),
    )
    db.add(approval)

    # Update decision status
    decision.status = ControllerDecisionStatus.AWAITING_APPROVAL
    db.commit()
    db.refresh(approval)

    # Audit
    AuditService(db).log(
        AuditAction.APPROVAL_REQUESTED,
        f"Approval requested for action {approval.requested_action} on exception {decision.exception_id}",
        merchant_id=merchant_id,
        entity_type="approval_request",
        entity_id=str(approval.id),
        metadata={
            "exception_id": str(decision.exception_id),
            "action": approval.requested_action,
            "risk_score": decision.risk_score,
            "confidence": decision.confidence,
        },
    )

    logger.info("Approval request created: %s for decision %s", approval.id, decision.id)
    return approval


def approve_request(
    db: Session,
    approval_id: uuid.UUID,
    user_id: uuid.UUID,
    user_role: Role,
    merchant_id: Optional[uuid.UUID] = None,
) -> ActionResult:
    """Approve a pending request and execute the action."""
    if user_role not in APPROVAL_ROLES:
        raise PermissionError(f"Role {user_role} cannot approve actions. Requires: {APPROVAL_ROLES}")

    approval = db.get(ApprovalRequest, approval_id)
    if not approval:
        raise ValueError(f"Approval request {approval_id} not found")
    if approval.status != ApprovalStatus.PENDING:
        raise ValueError(f"Approval request is not PENDING (current: {approval.status})")

    # Check expiry
    if approval.expires_at and datetime.now(timezone.utc) > approval.expires_at:
        approval.status = ApprovalStatus.EXPIRED
        db.commit()
        raise ValueError("Approval request has expired")

    # Mark as approved
    approval.status = ApprovalStatus.APPROVED
    approval.approved_by = user_id
    approval.approved_at = datetime.now(timezone.utc)
    db.commit()

    # Load the decision
    decision = db.get(ControllerDecision, approval.decision_id)
    if not decision:
        raise ValueError(f"Decision {approval.decision_id} not found")

    # Execute the action
    result = execute_action(
        db=db,
        decision=decision,
        action_type=approval.requested_action,
        exception_id=approval.exception_id,
        executed_by=f"user:{user_id}",
        user_id=user_id,
        merchant_id=merchant_id,
    )

    # Update decision status
    decision.status = ControllerDecisionStatus.EXECUTED
    db.commit()

    # Audit
    AuditService(db).log(
        AuditAction.ACTION_APPROVED,
        f"Action {approval.requested_action} approved by {user_id}",
        user_id=user_id,
        merchant_id=merchant_id,
        entity_type="approval_request",
        entity_id=str(approval.id),
        metadata={
            "exception_id": str(approval.exception_id),
            "action": approval.requested_action,
            "action_result_id": str(result.id),
        },
    )

    logger.info("Approval %s approved by user %s", approval_id, user_id)
    return result


def reject_request(
    db: Session,
    approval_id: uuid.UUID,
    user_id: uuid.UUID,
    user_role: Role,
    rejection_reason: str,
    merchant_id: Optional[uuid.UUID] = None,
) -> ApprovalRequest:
    """Reject a pending approval request with a mandatory reason."""
    if user_role not in REJECTION_ROLES:
        raise PermissionError(f"Role {user_role} cannot reject actions.")

    if not rejection_reason or not rejection_reason.strip():
        raise ValueError("Rejection reason is required")

    approval = db.get(ApprovalRequest, approval_id)
    if not approval:
        raise ValueError(f"Approval request {approval_id} not found")
    if approval.status != ApprovalStatus.PENDING:
        raise ValueError(f"Approval request is not PENDING (current: {approval.status})")

    approval.status = ApprovalStatus.REJECTED
    approval.rejected_by = user_id
    approval.rejected_at = datetime.now(timezone.utc)
    approval.rejection_reason = rejection_reason.strip()

    # Update decision status
    decision = db.get(ControllerDecision, approval.decision_id)
    if decision:
        decision.status = ControllerDecisionStatus.REJECTED
    db.commit()
    db.refresh(approval)

    # Audit
    AuditService(db).log(
        AuditAction.ACTION_REJECTED,
        f"Action rejected by {user_id}: {rejection_reason[:200]}",
        user_id=user_id,
        merchant_id=merchant_id,
        entity_type="approval_request",
        entity_id=str(approval.id),
        metadata={
            "exception_id": str(approval.exception_id),
            "action": approval.requested_action,
            "rejection_reason": rejection_reason[:500],
        },
    )

    logger.info("Approval %s rejected by user %s", approval_id, user_id)
    return approval
