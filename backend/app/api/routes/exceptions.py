"""Exception routes — list, detail, and status update."""

import uuid
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser, require_role
from app.core.database import get_db
from app.models.audit_log import AuditAction
from app.models.exception import ExceptionSeverity, ExceptionStatus, ExceptionType
from app.models.user import Role
from app.schemas.exception import ExceptionListResponse, ExceptionResponse, ExceptionUpdateRequest
from app.services.audit_service import AuditService
from app.services.exception_service import ExceptionService

router = APIRouter(prefix="/exceptions", tags=["Exceptions"])

# Roles that can modify exception status
_MODIFIER_ROLES = (Role.ADMIN, Role.FINANCE_MANAGER, Role.FINANCE_ANALYST)


@router.get("", response_model=ExceptionListResponse, summary="List exceptions with filtering")
def list_exceptions(
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    status: Optional[ExceptionStatus] = Query(None),
    severity: Optional[ExceptionSeverity] = Query(None),
    exception_type: Optional[ExceptionType] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> ExceptionListResponse:
    return ExceptionService(db).list_exceptions(
        status=status, severity=severity, exception_type=exception_type,
        page=page, page_size=page_size,
    )


@router.get("/{exception_id}", response_model=ExceptionResponse, summary="Get a single exception")
def get_exception(
    exception_id: uuid.UUID,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> ExceptionResponse:
    result = ExceptionService(db).get_exception(exception_id)
    AuditService(db).log(
        action=AuditAction.VIEW_EXCEPTION,
        description=f"Exception {exception_id} viewed",
        user_id=current_user.id,
        entity_type="exception",
        entity_id=str(exception_id),
    )
    return result


@router.patch(
    "/{exception_id}",
    response_model=ExceptionResponse,
    summary="Update exception status",
    dependencies=[require_role(*_MODIFIER_ROLES)],
)
def update_exception(
    exception_id: uuid.UUID,
    body: ExceptionUpdateRequest,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> ExceptionResponse:
    """Update the status of an exception. Requires ADMIN, FINANCE_MANAGER, or FINANCE_ANALYST role."""
    result = ExceptionService(db).update_status(exception_id, body.status)
    AuditService(db).log(
        action=AuditAction.UPDATE_EXCEPTION,
        description=f"Exception {exception_id} status changed to {body.status}",
        user_id=current_user.id,
        entity_type="exception",
        entity_id=str(exception_id),
        metadata={"new_status": body.status},
    )
    return result
