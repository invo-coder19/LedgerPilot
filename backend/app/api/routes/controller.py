"""Controller API routes — runs, decisions, metrics."""

from __future__ import annotations

import math
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser, require_role
from app.core.database import get_db
from app.models.controller import (
    ControllerDecision, ControllerRun, ControllerRunStatus,
)
from app.models.user import Role
from app.schemas.controller import (
    ControllerDecisionListResponse, ControllerDecisionResponse,
    ControllerRunCreate, ControllerRunListResponse, ControllerRunResponse,
    ControllerMetricsResponse,
)

router = APIRouter(prefix="/controller", tags=["Controller"])


@router.post(
    "/runs",
    response_model=ControllerRunResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_controller_run(
    body: ControllerRunCreate,
    current_user: CurrentUser = require_role(Role.ADMIN, Role.FINANCE_MANAGER),
    db: Session = Depends(get_db),
):
    """Start a new controller run across all eligible exceptions."""
    from app.controller.controller_service import start_controller_run

    # Get first merchant (demo — single tenant)
    from app.models.merchant import Merchant
    merchant = db.query(Merchant).first()
    if not merchant:
        raise HTTPException(status_code=404, detail="No merchant found")

    try:
        run = start_controller_run(
            db=db,
            merchant_id=merchant.id,
            reconciliation_run_id=body.reconciliation_run_id,
            dry_run=body.dry_run,
            user_id=current_user.id,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return ControllerRunResponse.model_validate(run)


@router.get("/runs", response_model=ControllerRunListResponse)
def list_controller_runs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: CurrentUser = require_role(
        Role.ADMIN, Role.FINANCE_MANAGER, Role.FINANCE_ANALYST
    ),
    db: Session = Depends(get_db),
):
    """List all controller runs."""
    query = db.query(ControllerRun).order_by(ControllerRun.created_at.desc())
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return ControllerRunListResponse(
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total else 0,
        items=[ControllerRunResponse.model_validate(r) for r in items],
    )


@router.get("/runs/{run_id}", response_model=ControllerRunResponse)
def get_controller_run(
    run_id: uuid.UUID,
    current_user: CurrentUser = require_role(
        Role.ADMIN, Role.FINANCE_MANAGER, Role.FINANCE_ANALYST
    ),
    db: Session = Depends(get_db),
):
    """Get controller run details with progress."""
    run = db.get(ControllerRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Controller run not found")
    return ControllerRunResponse.model_validate(run)


@router.get("/runs/{run_id}/decisions", response_model=ControllerDecisionListResponse)
def list_run_decisions(
    run_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: CurrentUser = require_role(
        Role.ADMIN, Role.FINANCE_MANAGER, Role.FINANCE_ANALYST
    ),
    db: Session = Depends(get_db),
):
    """List decisions for a controller run."""
    query = (
        db.query(ControllerDecision)
        .filter(ControllerDecision.controller_run_id == run_id)
        .order_by(ControllerDecision.created_at.desc())
    )
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return ControllerDecisionListResponse(
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total else 0,
        items=[ControllerDecisionResponse.model_validate(d) for d in items],
    )


@router.get("/decisions/{decision_id}", response_model=ControllerDecisionResponse)
def get_decision(
    decision_id: uuid.UUID,
    current_user: CurrentUser = require_role(
        Role.ADMIN, Role.FINANCE_MANAGER, Role.FINANCE_ANALYST
    ),
    db: Session = Depends(get_db),
):
    """Get a single controller decision with full detail."""
    decision = db.get(ControllerDecision, decision_id)
    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")
    return ControllerDecisionResponse.model_validate(decision)


@router.get("/metrics", response_model=ControllerMetricsResponse)
def get_metrics(
    current_user: CurrentUser = require_role(
        Role.ADMIN, Role.FINANCE_MANAGER, Role.FINANCE_ANALYST
    ),
    db: Session = Depends(get_db),
):
    """Get controller performance metrics."""
    from app.controller.controller_service import get_controller_metrics
    return get_controller_metrics(db)
