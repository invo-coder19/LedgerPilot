"""Audit log routes."""

import uuid
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser, require_role
from app.core.database import get_db
from app.models.audit_log import AuditAction
from app.models.user import Role
from app.schemas.audit_log import AuditLogListResponse, AuditLogResponse
from app.services.audit_log_service import AuditLogService

router = APIRouter(prefix="/audit-logs", tags=["Audit Logs"])

# Only ADMIN and FINANCE_MANAGER can read audit logs
_READER_ROLES = (Role.ADMIN, Role.FINANCE_MANAGER)


@router.get(
    "",
    response_model=AuditLogListResponse,
    summary="List audit log events",
    dependencies=[require_role(*_READER_ROLES)],
)
def list_audit_logs(
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    action: Optional[AuditAction] = Query(None),
    entity_type: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> AuditLogListResponse:
    return AuditLogService(db).list_audit_logs(
        action=action, entity_type=entity_type, page=page, page_size=page_size,
    )


@router.get(
    "/{log_id}",
    response_model=AuditLogResponse,
    summary="Get a single audit log entry",
    dependencies=[require_role(*_READER_ROLES)],
)
def get_audit_log(
    log_id: uuid.UUID,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> AuditLogResponse:
    return AuditLogService(db).get_audit_log(log_id)
