"""Invoice Pydantic schemas."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from app.models.invoice import InvoiceStatus
from app.schemas.common import ORMBase


class InvoiceResponse(ORMBase):
    id: uuid.UUID
    merchant_id: uuid.UUID
    invoice_id: str
    customer_id: Optional[str]
    amount: Decimal
    tax: Decimal
    status: InvoiceStatus
    invoice_date: date
    due_date: date
    payment_reference: Optional[str]
    created_at: datetime
    updated_at: datetime


class InvoiceListResponse(ORMBase):
    total: int
    page: int
    page_size: int
    pages: int
    items: list[InvoiceResponse]
