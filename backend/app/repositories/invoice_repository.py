"""Invoice repository."""

import uuid
from typing import Optional

from sqlalchemy.orm import Session

from app.models.invoice import Invoice, InvoiceStatus


class InvoiceRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, invoice_id: uuid.UUID) -> Optional[Invoice]:
        return self.db.get(Invoice, invoice_id)

    def list_paginated(
        self,
        merchant_id: Optional[uuid.UUID] = None,
        status: Optional[InvoiceStatus] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Invoice], int]:
        query = self.db.query(Invoice)

        if merchant_id:
            query = query.filter(Invoice.merchant_id == merchant_id)
        if status:
            query = query.filter(Invoice.status == status)
        if search:
            query = query.filter(Invoice.invoice_id.ilike(f"%{search}%"))

        total = query.count()
        items = (
            query.order_by(Invoice.invoice_date.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return items, total
