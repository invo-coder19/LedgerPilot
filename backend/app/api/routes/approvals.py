"""Approval API routes — list, approve, reject."""

from __future__ import annotations

import math
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser, require_role
from app.core.database import get_db
from app.models.controller import ApprovalRequest, ApprovalStatus
from app.models.user import Role
from app.schemas.controller import (
    ApprovalListResponse, ApprovalResponse,
    ApproveRequest, RejectRequest, ActionResultResponse,
)

router = APIRouter(prefix="/approvals", tags=["Approvals"])


@router.get("", response_model=ApprovalListResponse)
def list_approvals(
    status_filter: ApprovalStatus | None = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: CurrentUser = require_role(
        Role.ADMIN, Role.FINANCE_MANAGER, Role.FINANCE_ANALYST
    ),
    db: Session = Depends(get_db),
):
    """List approval requests. Analysts can view; managers can act."""
    query = db.query(ApprovalRequest).order_by(ApprovalRequest.requested_at.desc())
    if status_filter:
        query = query.filter(ApprovalRequest.status == status_filter)
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return ApprovalListResponse(
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total else 0,
        items=[ApprovalResponse.model_validate(a) for a in items],
    )


@router.get("/{approval_id}", response_model=ApprovalResponse)
def get_approval(
    approval_id: uuid.UUID,
    current_user: CurrentUser = require_role(
        Role.ADMIN, Role.FINANCE_MANAGER, Role.FINANCE_ANALYST
    ),
    db: Session = Depends(get_db),
):
    """Get approval request detail."""
    approval = db.get(ApprovalRequest, approval_id)
    if not approval:
        raise HTTPException(status_code=404, detail="Approval request not found")
    return ApprovalResponse.model_validate(approval)


@router.post("/{approval_id}/approve", response_model=ActionResultResponse)
def approve_action(
    approval_id: uuid.UUID,
    body: ApproveRequest = ApproveRequest(),
    current_user: CurrentUser = require_role(Role.ADMIN, Role.FINANCE_MANAGER),
    db: Session = Depends(get_db),
):
    """Approve a pending action. Only FINANCE_MANAGER and ADMIN."""
    from app.controller.approval_service import approve_request

    try:
        result = approve_request(
            db=db,
            approval_id=approval_id,
            user_id=current_user.id,
            user_role=current_user.role,
        )
        return ActionResultResponse.model_validate(result)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{approval_id}/reject", response_model=ApprovalResponse)
def reject_action(
    approval_id: uuid.UUID,
    body: RejectRequest,
    current_user: CurrentUser = require_role(Role.ADMIN, Role.FINANCE_MANAGER),
    db: Session = Depends(get_db),
):
    """Reject a pending action with mandatory reason. Only FINANCE_MANAGER and ADMIN."""
    from app.controller.approval_service import reject_request

    try:
        approval = reject_request(
            db=db,
            approval_id=approval_id,
            user_id=current_user.id,
            user_role=current_user.role,
            rejection_reason=body.reason,
        )
        return ApprovalResponse.model_validate(approval)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
