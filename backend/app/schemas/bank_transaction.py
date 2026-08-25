"""Bank transaction Pydantic schemas."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from app.models.bank_transaction import BankTransactionType
from app.schemas.common import ORMBase


class BankTransactionResponse(ORMBase):
    id: uuid.UUID
    merchant_id: uuid.UUID
    bank_transaction_id: str
    reference: Optional[str]
    amount: Decimal
    transaction_type: BankTransactionType
    transaction_date: date
    description: Optional[str]
    created_at: datetime
    updated_at: datetime


class BankTransactionListResponse(ORMBase):
    total: int
    page: int
    page_size: int
    pages: int
    items: list[BankTransactionResponse]
