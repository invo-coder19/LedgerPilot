"""Investigation API routes — Phase 3B.

Routes:
  POST /api/v1/exceptions/{id}/investigate          — start investigation
  GET  /api/v1/investigations/{id}                   — get run + result
  GET  /api/v1/investigations/{id}/steps             — timeline
  GET  /api/v1/exceptions/{id}/investigations        — list all runs for exception
"""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser
from app.agents.investigator import run_investigation
from app.core.database import get_db
from app.models.merchant import Merchant
from app.repositories.investigation_repository import InvestigationRepository
from app.schemas.investigation import (
    InvestigationRunResponse,
    InvestigationStepResponse,
    StartInvestigationResponse,
)

router = APIRouter(tags=["AI Investigation"])


def _resolve_merchant_id(db: Session) -> Optional[uuid.UUID]:
    merchant = db.query(Merchant).first()
    return merchant.id if merchant else None


def _run_response(run, steps=None) -> InvestigationRunResponse:
    return InvestigationRunResponse(
        id=str(run.id),
        exception_id=str(run.exception_id),
        merchant_id=str(run.merchant_id) if run.merchant_id else None,
        status=str(run.status.value),
        started_at=run.started_at,
        completed_at=run.completed_at,
        model_provider=run.model_provider,
        model_name=run.model_name,
        final_result=run.final_result,
        final_confidence=run.final_confidence,
        confidence_band=run.confidence_band,
        requires_human=run.requires_human,
        error_message=run.error_message,
        duration_ms=run.duration_ms,
        steps=[
            InvestigationStepResponse(
                id=str(s.id),
                step_name=s.step_name,
                tool_name=s.tool_name,
                input_summary=s.input_summary,
                output_summary=s.output_summary,
                duration_ms=s.duration_ms,
                created_at=s.created_at,
            )
            for s in (steps or run.steps or [])
        ],
    )


@router.post(
    "/exceptions/{exception_id}/investigate",
    response_model=StartInvestigationResponse,
    summary="Trigger AI investigation for an exception",
)
def investigate_exception(
    exception_id: str,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
) -> StartInvestigationResponse:
    """Start an AI investigation for a financial exception.

    Runs synchronously and returns the full result.
    The investigation_id can be used to retrieve the result later.
    """
    merchant_id = _resolve_merchant_id(db)

    # Validate the exception exists first
    try:
        exc_uuid = uuid.UUID(exception_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid exception ID format")

    from app.models.exception import Exception as FinancialException
    exc = db.get(FinancialException, exc_uuid)
    if exc is None:
        raise HTTPException(status_code=404, detail="Exception not found")

    result = run_investigation(
        db=db,
        exception_id=exception_id,
        merchant_id=merchant_id,
        user_id=current_user.id,
    )

    return StartInvestigationResponse(
        investigation_id=result["investigation_id"],
        status=result["status"],
        result=result.get("result"),
        error=result.get("error"),
        message=(
            "Investigation complete." if result["status"] == "COMPLETED"
            else f"Investigation failed: {result.get('error', 'Unknown error')}"
        ),
    )


@router.get(
    "/investigations/{investigation_id}",
    response_model=InvestigationRunResponse,
    summary="Get investigation result",
)
def get_investigation(
    investigation_id: str,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
) -> InvestigationRunResponse:
    """Retrieve an investigation run with its final result."""
    try:
        run_uuid = uuid.UUID(investigation_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid investigation ID format")

    repo = InvestigationRepository(db)
    run = repo.get_run(run_uuid, with_steps=True)
    if run is None:
        raise HTTPException(status_code=404, detail="Investigation not found")

    return _run_response(run)


@router.get(
    "/investigations/{investigation_id}/steps",
    response_model=list[InvestigationStepResponse],
    summary="Get investigation timeline",
)
def get_investigation_steps(
    investigation_id: str,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
) -> list[InvestigationStepResponse]:
    """Get the investigation step-by-step timeline."""
    try:
        run_uuid = uuid.UUID(investigation_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid investigation ID format")

    repo = InvestigationRepository(db)
    steps = repo.get_steps(run_uuid)

    return [
        InvestigationStepResponse(
            id=str(s.id),
            step_name=s.step_name,
            tool_name=s.tool_name,
            input_summary=s.input_summary,
            output_summary=s.output_summary,
            duration_ms=s.duration_ms,
            created_at=s.created_at,
        )
        for s in steps
    ]


@router.get(
    "/exceptions/{exception_id}/investigations",
    response_model=list[InvestigationRunResponse],
    summary="List all investigations for an exception",
)
def list_exception_investigations(
    exception_id: str,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
) -> list[InvestigationRunResponse]:
    """List all investigation runs for a given exception."""
    try:
        exc_uuid = uuid.UUID(exception_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid exception ID format")

    merchant_id = _resolve_merchant_id(db)
    repo = InvestigationRepository(db)
    runs = repo.list_for_exception(exc_uuid, merchant_id)
    return [_run_response(r) for r in runs]
