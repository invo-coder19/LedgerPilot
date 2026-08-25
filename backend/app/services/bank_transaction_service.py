"""Bank transaction service."""

import math
import uuid
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.bank_transaction import BankTransactionType
from app.repositories.bank_transaction_repository import BankTransactionRepository
from app.schemas.bank_transaction import BankTransactionListResponse, BankTransactionResponse


class BankTransactionService:
    def __init__(self, db: Session) -> None:
        self.repo = BankTransactionRepository(db)

    def list_bank_transactions(
        self,
        merchant_id: Optional[uuid.UUID] = None,
        transaction_type: Optional[BankTransactionType] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> BankTransactionListResponse:
        items, total = self.repo.list_paginated(
            merchant_id=merchant_id, transaction_type=transaction_type,
            page=page, page_size=page_size,
        )
        pages = math.ceil(total / page_size) if total else 0
        return BankTransactionListResponse(
            total=total, page=page, page_size=page_size, pages=pages,
            items=[BankTransactionResponse.model_validate(b) for b in items],
        )

    def get_bank_transaction(self, bt_id: uuid.UUID) -> BankTransactionResponse:
        bt = self.repo.get_by_id(bt_id)
        if not bt:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bank transaction not found")
        return BankTransactionResponse.model_validate(bt)
