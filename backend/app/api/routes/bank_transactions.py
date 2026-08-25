"""Bank transaction routes."""

import uuid
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser
from app.core.database import get_db
from app.models.audit_log import AuditAction
from app.models.bank_transaction import BankTransactionType
from app.schemas.bank_transaction import BankTransactionListResponse, BankTransactionResponse
from app.services.audit_service import AuditService
from app.services.bank_transaction_service import BankTransactionService

router = APIRouter(prefix="/bank-transactions", tags=["Bank Transactions"])


@router.get("", response_model=BankTransactionListResponse, summary="List bank transactions")
def list_bank_transactions(
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    transaction_type: Optional[BankTransactionType] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> BankTransactionListResponse:
    return BankTransactionService(db).list_bank_transactions(
        transaction_type=transaction_type, page=page, page_size=page_size,
    )


@router.get("/{bt_id}", response_model=BankTransactionResponse, summary="Get a single bank transaction")
def get_bank_transaction(
    bt_id: uuid.UUID,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> BankTransactionResponse:
    result = BankTransactionService(db).get_bank_transaction(bt_id)
    AuditService(db).log(
        action=AuditAction.VIEW_BANK_TRANSACTION,
        description=f"Bank transaction {bt_id} viewed",
        user_id=current_user.id,
        entity_type="bank_transaction",
        entity_id=str(bt_id),
    )
    return result
