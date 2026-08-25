"""Audit service — centralized audit event creation.

All important user actions should go through this service.
Do NOT log passwords, JWT tokens, or any sensitive secrets.
"""

import uuid
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models.audit_log import AuditAction, AuditLog
from app.repositories.audit_log_repository import AuditLogRepository


class AuditService:
    def __init__(self, db: Session) -> None:
        self.repo = AuditLogRepository(db)

    def log(
        self,
        action: AuditAction,
        description: str,
        user_id: Optional[uuid.UUID] = None,
        merchant_id: Optional[uuid.UUID] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> AuditLog:
        """Create and persist an audit log entry."""
        log = AuditLog(
            user_id=user_id,
            merchant_id=merchant_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            description=description,
            metadata_=metadata,
        )
        return self.repo.create(log)
