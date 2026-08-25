"""Settlement Pydantic schemas."""

import uuid
from datetime import date, datetime
from decimal import Decimal

from app.models.settlement import SettlementStatus
from app.schemas.common import ORMBase


class SettlementResponse(ORMBase):
    id: uuid.UUID
    merchant_id: uuid.UUID
    settlement_id: str
    payment_id: str
    settlement_amount: Decimal
    fee: Decimal
    settlement_date: date
    status: SettlementStatus
    created_at: datetime
    updated_at: datetime


class SettlementListResponse(ORMBase):
    total: int
    page: int
    page_size: int
    pages: int
    items: list[SettlementResponse]
