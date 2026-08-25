"""Bank transaction repository."""

import uuid
from typing import Optional

from sqlalchemy.orm import Session

from app.models.bank_transaction import BankTransaction, BankTransactionType


class BankTransactionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, bt_id: uuid.UUID) -> Optional[BankTransaction]:
        return self.db.get(BankTransaction, bt_id)

    def list_paginated(
        self,
        merchant_id: Optional[uuid.UUID] = None,
        transaction_type: Optional[BankTransactionType] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[BankTransaction], int]:
        query = self.db.query(BankTransaction)

        if merchant_id:
            query = query.filter(BankTransaction.merchant_id == merchant_id)
        if transaction_type:
            query = query.filter(BankTransaction.transaction_type == transaction_type)

        total = query.count()
        items = (
            query.order_by(BankTransaction.transaction_date.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return items, total
