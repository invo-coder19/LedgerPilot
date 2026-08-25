"""Exception Pydantic schemas."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel

from app.models.exception import ExceptionType, ExceptionSeverity, ExceptionStatus
from app.schemas.common import ORMBase


class ExceptionResponse(ORMBase):
    id: uuid.UUID
    merchant_id: uuid.UUID
    source_type: str
    source_id: str
    exception_type: ExceptionType
    severity: ExceptionSeverity
    amount: Optional[Decimal]
    description: str
    status: ExceptionStatus
    created_at: datetime
    updated_at: datetime


class ExceptionUpdateRequest(BaseModel):
    status: ExceptionStatus


class ExceptionListResponse(ORMBase):
    total: int
    page: int
    page_size: int
    pages: int
    items: list[ExceptionResponse]
