"""Audit log service — listing and retrieval."""

import math
import uuid
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.audit_log import AuditAction
from app.repositories.audit_log_repository import AuditLogRepository
from app.schemas.audit_log import AuditLogListResponse, AuditLogResponse


class AuditLogService:
    def __init__(self, db: Session) -> None:
        self.repo = AuditLogRepository(db)

    def list_audit_logs(
        self,
        user_id: Optional[uuid.UUID] = None,
        merchant_id: Optional[uuid.UUID] = None,
        action: Optional[AuditAction] = None,
        entity_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> AuditLogListResponse:
        items, total = self.repo.list_paginated(
            user_id=user_id,
            merchant_id=merchant_id,
            action=action,
            entity_type=entity_type,
            page=page,
            page_size=page_size,
        )
        pages = math.ceil(total / page_size) if total else 0
        return AuditLogListResponse(
            total=total, page=page, page_size=page_size, pages=pages,
            items=[AuditLogResponse.model_validate(l) for l in items],
        )

    def get_audit_log(self, log_id: uuid.UUID) -> AuditLogResponse:
        log = self.repo.get_by_id(log_id)
        if not log:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit log not found")
        return AuditLogResponse.model_validate(log)

    def get_recent(self, limit: int = 10) -> list[AuditLogResponse]:
        items = self.repo.recent(limit=limit)
        return [AuditLogResponse.model_validate(l) for l in items]
