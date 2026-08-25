"""Transaction repository — data access with filtering and pagination."""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models.transaction import Transaction, TransactionStatus


class TransactionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, transaction_id: uuid.UUID) -> Optional[Transaction]:
        return self.db.get(Transaction, transaction_id)

    def list_paginated(
        self,
        merchant_id: Optional[uuid.UUID] = None,
        status: Optional[TransactionStatus] = None,
        search: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Transaction], int]:
        query = self.db.query(Transaction)

        if merchant_id:
            query = query.filter(Transaction.merchant_id == merchant_id)
        if status:
            query = query.filter(Transaction.status == status)
        if search:
            query = query.filter(
                or_(
                    Transaction.payment_id.ilike(f"%{search}%"),
                    Transaction.order_id.ilike(f"%{search}%"),
                    Transaction.customer_id.ilike(f"%{search}%"),
                )
            )
        if date_from:
            query = query.filter(Transaction.transaction_timestamp >= date_from)
        if date_to:
            query = query.filter(Transaction.transaction_timestamp <= date_to)

        total = query.count()
        items = (
            query.order_by(Transaction.transaction_timestamp.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return items, total

    def count_by_status(self) -> dict[str, int]:
        rows = (
            self.db.query(Transaction.status, func.count(Transaction.id))
            .group_by(Transaction.status)
            .all()
        )
        return {str(row[0]): row[1] for row in rows}

    def sum_amount(self) -> float:
        result = self.db.query(func.sum(Transaction.amount)).scalar()
        return result or 0

    def volume_over_time(self, days: int = 30) -> list[dict]:
        """Return daily transaction count and amount for the last N days."""
        rows = (
            self.db.query(
                func.date(Transaction.transaction_timestamp).label("date"),
                func.count(Transaction.id).label("count"),
                func.sum(Transaction.amount).label("amount"),
            )
            .group_by(func.date(Transaction.transaction_timestamp))
            .order_by(func.date(Transaction.transaction_timestamp))
            .limit(days)
            .all()
        )
        return [{"date": str(r.date), "count": r.count, "amount": r.amount or 0} for r in rows]
