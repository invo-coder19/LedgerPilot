"""Investigation repository — CRUD for investigation runs and steps."""

from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy.orm import Session, joinedload

from app.models.investigation import AIInvestigationRun, AIInvestigationStep, InvestigationStatus


class InvestigationRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_run(self, run_id: uuid.UUID, with_steps: bool = False) -> Optional[AIInvestigationRun]:
        q = self.db.query(AIInvestigationRun)
        if with_steps:
            q = q.options(joinedload(AIInvestigationRun.steps))
        return q.filter(AIInvestigationRun.id == run_id).first()

    def list_for_exception(
        self,
        exception_id: uuid.UUID,
        merchant_id: Optional[uuid.UUID] = None,
        limit: int = 10,
    ) -> list[AIInvestigationRun]:
        q = self.db.query(AIInvestigationRun).filter(
            AIInvestigationRun.exception_id == exception_id
        )
        if merchant_id:
            q = q.filter(
                (AIInvestigationRun.merchant_id == merchant_id)
                | (AIInvestigationRun.merchant_id.is_(None))
            )
        return q.order_by(AIInvestigationRun.started_at.desc()).limit(limit).all()

    def get_steps(self, run_id: uuid.UUID) -> list[AIInvestigationStep]:
        return (
            self.db.query(AIInvestigationStep)
            .filter(AIInvestigationStep.investigation_id == run_id)
            .order_by(AIInvestigationStep.created_at)
            .all()
        )
