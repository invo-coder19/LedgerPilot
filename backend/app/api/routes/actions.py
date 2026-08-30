"""Action history and rollback API routes."""

from __future__ import annotations

import math
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser, require_role
from app.core.database import get_db
from app.models.controller import ActionResult
from app.models.user import Role
from app.schemas.controller import ActionResultListResponse, ActionResultResponse

router = APIRouter(prefix="/actions", tags=["Actions"])


@router.get("", response_model=ActionResultListResponse)
def list_actions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: CurrentUser = require_role(
        Role.ADMIN, Role.FINANCE_MANAGER, Role.FINANCE_ANALYST
    ),
    db: Session = Depends(get_db),
):
    """List all action results."""
    query = db.query(ActionResult).order_by(ActionResult.executed_at.desc())
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return ActionResultListResponse(
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total else 0,
        items=[ActionResultResponse.model_validate(a) for a in items],
    )


@router.get("/{action_id}", response_model=ActionResultResponse)
def get_action(
    action_id: uuid.UUID,
    current_user: CurrentUser = require_role(
        Role.ADMIN, Role.FINANCE_MANAGER, Role.FINANCE_ANALYST
    ),
    db: Session = Depends(get_db),
):
    """Get a single action result."""
    result = db.get(ActionResult, action_id)
    if not result:
        raise HTTPException(status_code=404, detail="Action result not found")
    return ActionResultResponse.model_validate(result)


@router.post("/{action_id}/rollback", response_model=ActionResultResponse)
def rollback_action(
    action_id: uuid.UUID,
    current_user: CurrentUser = require_role(Role.ADMIN, Role.FINANCE_MANAGER),
    db: Session = Depends(get_db),
):
    """Rollback a reversible action. Only FINANCE_MANAGER and ADMIN."""
    from app.controller.rollback import rollback_action as do_rollback, RollbackError

    try:
        result = do_rollback(
            db=db,
            action_result_id=action_id,
            user_id=current_user.id,
        )
        return ActionResultResponse.model_validate(result)
    except RollbackError as e:
        raise HTTPException(status_code=400, detail=str(e))
