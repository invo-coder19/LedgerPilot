"""Audit log Pydantic schemas."""

import uuid
from datetime import datetime
from typing import Any, Optional

from app.models.audit_log import AuditAction
from app.schemas.common import ORMBase


class AuditLogResponse(ORMBase):
    id: uuid.UUID
    user_id: Optional[uuid.UUID]
    merchant_id: Optional[uuid.UUID]
    action: AuditAction
    entity_type: Optional[str]
    entity_id: Optional[str]
    description: str
    metadata_: Optional[dict[str, Any]]
    created_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}


class AuditLogListResponse(ORMBase):
    total: int
    page: int
    page_size: int
    pages: int
    items: list[AuditLogResponse]
