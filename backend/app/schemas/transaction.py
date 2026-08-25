"""Transaction Pydantic schemas."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from app.models.transaction import TransactionStatus
from app.schemas.common import ORMBase


class TransactionResponse(ORMBase):
    id: uuid.UUID
    merchant_id: uuid.UUID
    payment_id: str
    order_id: str
    customer_id: Optional[str]
    amount: Decimal
    fee: Decimal
    tax: Decimal
    status: TransactionStatus
    payment_method: Optional[str]
    transaction_timestamp: datetime
    created_at: datetime
    updated_at: datetime


class TransactionListResponse(ORMBase):
    total: int
    page: int
    page_size: int
    pages: int
    items: list[TransactionResponse]
