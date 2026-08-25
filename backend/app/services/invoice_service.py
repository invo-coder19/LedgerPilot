"""Invoice service."""

import math
import uuid
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.invoice import InvoiceStatus
from app.repositories.invoice_repository import InvoiceRepository
from app.schemas.invoice import InvoiceListResponse, InvoiceResponse


class InvoiceService:
    def __init__(self, db: Session) -> None:
        self.repo = InvoiceRepository(db)

    def list_invoices(
        self,
        merchant_id: Optional[uuid.UUID] = None,
        inv_status: Optional[InvoiceStatus] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> InvoiceListResponse:
        items, total = self.repo.list_paginated(
            merchant_id=merchant_id, status=inv_status, search=search,
            page=page, page_size=page_size,
        )
        pages = math.ceil(total / page_size) if total else 0
        return InvoiceListResponse(
            total=total, page=page, page_size=page_size, pages=pages,
            items=[InvoiceResponse.model_validate(i) for i in items],
        )

    def get_invoice(self, invoice_id: uuid.UUID) -> InvoiceResponse:
        inv = self.repo.get_by_id(invoice_id)
        if not inv:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
        return InvoiceResponse.model_validate(inv)
