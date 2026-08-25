"""Transaction service."""

import math
import uuid
from datetime import datetime
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.transaction import TransactionStatus
from app.repositories.transaction_repository import TransactionRepository
from app.schemas.transaction import TransactionListResponse, TransactionResponse


class TransactionService:
    def __init__(self, db: Session) -> None:
        self.repo = TransactionRepository(db)

    def list_transactions(
        self,
        merchant_id: Optional[uuid.UUID] = None,
        status: Optional[TransactionStatus] = None,
        search: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> TransactionListResponse:
        items, total = self.repo.list_paginated(
            merchant_id=merchant_id,
            status=status,
            search=search,
            date_from=date_from,
            date_to=date_to,
            page=page,
            page_size=page_size,
        )
        pages = math.ceil(total / page_size) if total else 0
        return TransactionListResponse(
            total=total, page=page, page_size=page_size, pages=pages,
            items=[TransactionResponse.model_validate(t) for t in items],
        )

    def get_transaction(self, transaction_id: uuid.UUID) -> TransactionResponse:
        tx = self.repo.get_by_id(transaction_id)
        if not tx:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
        return TransactionResponse.model_validate(tx)
