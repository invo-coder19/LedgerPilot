"""Settlement routes."""

import uuid
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser
from app.core.database import get_db
from app.models.audit_log import AuditAction
from app.models.settlement import SettlementStatus
from app.schemas.settlement import SettlementListResponse, SettlementResponse
from app.services.audit_service import AuditService
from app.services.settlement_service import SettlementService

router = APIRouter(prefix="/settlements", tags=["Settlements"])


@router.get("", response_model=SettlementListResponse, summary="List settlements")
def list_settlements(
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    status: Optional[SettlementStatus] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> SettlementListResponse:
    return SettlementService(db).list_settlements(
        stl_status=status, page=page, page_size=page_size,
    )


@router.get("/{settlement_id}", response_model=SettlementResponse, summary="Get a single settlement")
def get_settlement(
    settlement_id: uuid.UUID,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> SettlementResponse:
    result = SettlementService(db).get_settlement(settlement_id)
    AuditService(db).log(
        action=AuditAction.VIEW_SETTLEMENT,
        description=f"Settlement {settlement_id} viewed",
        user_id=current_user.id,
        entity_type="settlement",
        entity_id=str(settlement_id),
    )
    return result
