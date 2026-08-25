"""Exception repository."""

import uuid
from typing import Optional

from sqlalchemy.orm import Session

from app.models.exception import Exception as FinancialException
from app.models.exception import ExceptionSeverity, ExceptionStatus, ExceptionType


class ExceptionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, exception_id: uuid.UUID) -> Optional[FinancialException]:
        return self.db.get(FinancialException, exception_id)

    def list_paginated(
        self,
        merchant_id: Optional[uuid.UUID] = None,
        status: Optional[ExceptionStatus] = None,
        severity: Optional[ExceptionSeverity] = None,
        exception_type: Optional[ExceptionType] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[FinancialException], int]:
        query = self.db.query(FinancialException)

        if merchant_id:
            query = query.filter(FinancialException.merchant_id == merchant_id)
        if status:
            query = query.filter(FinancialException.status == status)
        if severity:
            query = query.filter(FinancialException.severity == severity)
        if exception_type:
            query = query.filter(FinancialException.exception_type == exception_type)

        total = query.count()
        items = (
            query.order_by(FinancialException.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return items, total

    def update_status(self, exception: FinancialException, status: ExceptionStatus) -> FinancialException:
        exception.status = status
        self.db.commit()
        self.db.refresh(exception)
        return exception

    def count_by_status(self) -> dict[str, int]:
        from sqlalchemy import func
        rows = (
            self.db.query(FinancialException.status, func.count(FinancialException.id))
            .group_by(FinancialException.status)
            .all()
        )
        return {str(row[0]): row[1] for row in rows}

    def recent(self, limit: int = 5) -> list[FinancialException]:
        return (
            self.db.query(FinancialException)
            .order_by(FinancialException.created_at.desc())
            .limit(limit)
            .all()
        )

    def trend_over_time(self) -> list[dict]:
        from sqlalchemy import func
        rows = (
            self.db.query(
                func.date(FinancialException.created_at).label("date"),
                FinancialException.status,
                func.count(FinancialException.id).label("count"),
            )
            .group_by(func.date(FinancialException.created_at), FinancialException.status)
            .order_by(func.date(FinancialException.created_at))
            .all()
        )
        return [{"date": str(r.date), "status": str(r.status), "count": r.count} for r in rows]
