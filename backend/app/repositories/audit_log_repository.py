"""Audit log repository."""

import uuid
from typing import Optional

from sqlalchemy.orm import Session

from app.models.audit_log import AuditAction, AuditLog


class AuditLogRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, log_id: uuid.UUID) -> Optional[AuditLog]:
        return self.db.get(AuditLog, log_id)

    def create(self, log: AuditLog) -> AuditLog:
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        return log

    def list_paginated(
        self,
        user_id: Optional[uuid.UUID] = None,
        merchant_id: Optional[uuid.UUID] = None,
        action: Optional[AuditAction] = None,
        entity_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[AuditLog], int]:
        query = self.db.query(AuditLog)

        if user_id:
            query = query.filter(AuditLog.user_id == user_id)
        if merchant_id:
            query = query.filter(AuditLog.merchant_id == merchant_id)
        if action:
            query = query.filter(AuditLog.action == action)
        if entity_type:
            query = query.filter(AuditLog.entity_type == entity_type)

        total = query.count()
        items = (
            query.order_by(AuditLog.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return items, total

    def recent(self, limit: int = 10) -> list[AuditLog]:
        return (
            self.db.query(AuditLog)
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
            .all()
        )
