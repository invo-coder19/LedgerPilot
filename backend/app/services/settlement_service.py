"""Settlement service."""

import math
import uuid
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.settlement import SettlementStatus
from app.repositories.settlement_repository import SettlementRepository
from app.schemas.settlement import SettlementListResponse, SettlementResponse


class SettlementService:
    def __init__(self, db: Session) -> None:
        self.repo = SettlementRepository(db)

    def list_settlements(
        self,
        merchant_id: Optional[uuid.UUID] = None,
        stl_status: Optional[SettlementStatus] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> SettlementListResponse:
        items, total = self.repo.list_paginated(
            merchant_id=merchant_id, status=stl_status,
            page=page, page_size=page_size,
        )
        pages = math.ceil(total / page_size) if total else 0
        return SettlementListResponse(
            total=total, page=page, page_size=page_size, pages=pages,
            items=[SettlementResponse.model_validate(s) for s in items],
        )

    def get_settlement(self, settlement_id: uuid.UUID) -> SettlementResponse:
        stl = self.repo.get_by_id(settlement_id)
        if not stl:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Settlement not found")
        return SettlementResponse.model_validate(stl)
