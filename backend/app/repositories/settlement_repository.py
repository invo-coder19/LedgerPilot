"""Settlement repository."""

import uuid
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.settlement import Settlement, SettlementStatus


class SettlementRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, settlement_id: uuid.UUID) -> Optional[Settlement]:
        return self.db.get(Settlement, settlement_id)

    def list_paginated(
        self,
        merchant_id: Optional[uuid.UUID] = None,
        status: Optional[SettlementStatus] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Settlement], int]:
        query = self.db.query(Settlement)

        if merchant_id:
            query = query.filter(Settlement.merchant_id == merchant_id)
        if status:
            query = query.filter(Settlement.status == status)

        total = query.count()
        items = (
            query.order_by(Settlement.settlement_date.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return items, total

    def sum_amount(self) -> float:
        result = self.db.query(func.sum(Settlement.settlement_amount)).scalar()
        return result or 0
