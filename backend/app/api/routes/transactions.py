"""Transaction routes."""

import uuid
from datetime import datetime
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser
from app.core.database import get_db
from app.models.audit_log import AuditAction
from app.models.transaction import TransactionStatus
from app.schemas.transaction import TransactionListResponse, TransactionResponse
from app.services.audit_service import AuditService
from app.services.transaction_service import TransactionService

router = APIRouter(prefix="/transactions", tags=["Transactions"])


@router.get("", response_model=TransactionListResponse, summary="List transactions with pagination and filtering")
def list_transactions(
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    status: Optional[TransactionStatus] = Query(None),
    search: Optional[str] = Query(None, description="Search by payment_id, order_id, or customer_id"),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> TransactionListResponse:
    return TransactionService(db).list_transactions(
        status=status, search=search, date_from=date_from, date_to=date_to,
        page=page, page_size=page_size,
    )


@router.get("/{transaction_id}", response_model=TransactionResponse, summary="Get a single transaction")
def get_transaction(
    transaction_id: uuid.UUID,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> TransactionResponse:
    result = TransactionService(db).get_transaction(transaction_id)
    AuditService(db).log(
        action=AuditAction.VIEW_TRANSACTION,
        description=f"Transaction {transaction_id} viewed",
        user_id=current_user.id,
        entity_type="transaction",
        entity_id=str(transaction_id),
    )
    return result
