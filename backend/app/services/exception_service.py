"""Exception service — business logic for exception management."""

import math
import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.exception import ExceptionStatus
from app.repositories.exception_repository import ExceptionRepository
from app.repositories.exception_repository import ExceptionSeverity, ExceptionType
from app.schemas.exception import ExceptionListResponse, ExceptionResponse


class ExceptionService:
    def __init__(self, db: Session) -> None:
        self.repo = ExceptionRepository(db)

    def list_exceptions(
        self,
        merchant_id: uuid.UUID | None = None,
        status: ExceptionStatus | None = None,
        severity: ExceptionSeverity | None = None,
        exception_type: ExceptionType | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> ExceptionListResponse:
        items, total = self.repo.list_paginated(
            merchant_id=merchant_id,
            status=status,
            severity=severity,
            exception_type=exception_type,
            page=page,
            page_size=page_size,
        )
        pages = math.ceil(total / page_size) if total else 0
        return ExceptionListResponse(
            total=total, page=page, page_size=page_size, pages=pages,
            items=[ExceptionResponse.model_validate(e) for e in items],
        )

    def get_exception(self, exception_id: uuid.UUID) -> ExceptionResponse:
        exc = self.repo.get_by_id(exception_id)
        if not exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exception not found")
        return ExceptionResponse.model_validate(exc)

    def update_status(self, exception_id: uuid.UUID, new_status: ExceptionStatus) -> ExceptionResponse:
        exc = self.repo.get_by_id(exception_id)
        if not exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exception not found")
        updated = self.repo.update_status(exc, new_status)
        return ExceptionResponse.model_validate(updated)

    def get_recent(self, limit: int = 5) -> list[ExceptionResponse]:
        items = self.repo.recent(limit=limit)
        return [ExceptionResponse.model_validate(e) for e in items]
