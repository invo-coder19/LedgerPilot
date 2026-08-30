"""Escalation service — routes high-risk/blocked cases to humans."""

from __future__ import annotations

import logging
import uuid
from typing import Optional

from sqlalchemy.orm import Session

from app.models.audit_log import AuditAction
from app.models.controller import (
    ControllerDecision, ControllerDecisionStatus,
)
from app.models.exception import Exception as FinancialException, ExceptionStatus
from app.services.audit_service import AuditService

logger = logging.getLogger(__name__)


def escalate_decision(
    db: Session,
    decision: ControllerDecision,
    merchant_id: Optional[uuid.UUID] = None,
) -> None:
    """Escalate a decision — mark exception as IN_REVIEW and decision as ESCALATED.

    Escalated cases MUST NOT execute any financial action.
    """
    decision.status = ControllerDecisionStatus.ESCALATED

    exception = db.get(FinancialException, decision.exception_id)
    if exception and exception.status == ExceptionStatus.OPEN:
        exception.status = ExceptionStatus.IN_REVIEW

    db.commit()

    AuditService(db).log(
        AuditAction.ACTION_ESCALATED,
        f"Exception {decision.exception_id} escalated: {decision.reason[:200]}",
        merchant_id=merchant_id,
        entity_type="exception",
        entity_id=str(decision.exception_id),
        metadata={
            "decision_id": str(decision.id),
            "risk_score": decision.risk_score,
            "confidence": decision.confidence,
            "risk_band": decision.risk_band.value if hasattr(decision.risk_band, 'value') else str(decision.risk_band),
        },
    )

    logger.info(
        "Decision %s escalated for exception %s (risk=%s confidence=%.2f)",
        decision.id, decision.exception_id,
        decision.risk_band, decision.confidence,
    )


def block_decision(
    db: Session,
    decision: ControllerDecision,
    merchant_id: Optional[uuid.UUID] = None,
) -> None:
    """Block a decision — no action may execute."""
    decision.status = ControllerDecisionStatus.BLOCKED
    db.commit()

    AuditService(db).log(
        AuditAction.ACTION_BLOCKED,
        f"Exception {decision.exception_id} blocked: {decision.reason[:200]}",
        merchant_id=merchant_id,
        entity_type="exception",
        entity_id=str(decision.exception_id),
        metadata={
            "decision_id": str(decision.id),
            "risk_score": decision.risk_score,
            "confidence": decision.confidence,
        },
    )

    logger.info("Decision %s blocked for exception %s", decision.id, decision.exception_id)
