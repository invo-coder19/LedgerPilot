"""Controller service — orchestrates the full Phase 4 pipeline.

Exception → Investigation → Risk → Policy → Decision → Action → Verify → Audit

This service is the single entry point for running the autonomous controller.
It calls reusable services (investigator, ML, etc.) — NO business logic duplication.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from app.controller import decision_engine
from app.controller.action_executor import execute_action
from app.controller.approval_service import create_approval_request
from app.controller.escalation_service import block_decision, escalate_decision
from app.models.audit_log import AuditAction
from app.models.controller import (
    ControllerDecision, ControllerDecisionStatus, ControllerDecisionType,
    ControllerRun, ControllerRunStatus, ControllerConfig,
)
from app.models.exception import Exception as FinancialException, ExceptionStatus
from app.models.investigation import AIInvestigationRun, InvestigationStatus
from app.services.audit_service import AuditService

logger = logging.getLogger(__name__)


def _get_config_value(db: Session, key: str, default=None):
    """Read a controller config value."""
    cfg = db.query(ControllerConfig).filter(ControllerConfig.key == key).first()
    if cfg:
        return cfg.value.get("value", default)
    return default


def start_controller_run(
    db: Session,
    merchant_id: uuid.UUID,
    reconciliation_run_id: Optional[str] = None,
    dry_run: bool = False,
    user_id: Optional[uuid.UUID] = None,
) -> ControllerRun:
    """Create and start a controller run for all OPEN exceptions of a merchant."""
    # Count eligible exceptions
    query = db.query(FinancialException).filter(
        FinancialException.merchant_id == merchant_id,
        FinancialException.status.in_([ExceptionStatus.OPEN, ExceptionStatus.IN_REVIEW]),
    )
    exceptions = query.all()

    run = ControllerRun(
        merchant_id=merchant_id,
        reconciliation_run_id=reconciliation_run_id,
        status=ControllerRunStatus.RUNNING,
        dry_run=dry_run,
        total_exceptions=len(exceptions),
        started_at=datetime.now(timezone.utc),
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    AuditService(db).log(
        AuditAction.CONTROLLER_RUN_STARTED,
        f"Controller run started: {len(exceptions)} exceptions, dry_run={dry_run}",
        user_id=user_id,
        merchant_id=merchant_id,
        entity_type="controller_run",
        entity_id=str(run.id),
        metadata={
            "total_exceptions": len(exceptions),
            "dry_run": dry_run,
            "reconciliation_run_id": reconciliation_run_id,
        },
    )

    logger.info(
        "Controller run %s started: %d exceptions, dry_run=%s",
        run.id, len(exceptions), dry_run,
    )

    # Process each exception
    for exc in exceptions:
        try:
            _process_exception(db, run, exc, dry_run, merchant_id, user_id)
        except Exception as e:
            logger.error("Failed to process exception %s: %s", exc.id, e, exc_info=True)
            run.failed += 1
            db.commit()

    # Finalize run
    _finalize_run(db, run, user_id, merchant_id)
    return run


def _process_exception(
    db: Session,
    run: ControllerRun,
    exception: FinancialException,
    dry_run: bool,
    merchant_id: uuid.UUID,
    user_id: Optional[uuid.UUID],
) -> None:
    """Process a single exception through the controller pipeline."""
    # ── 1. Find latest completed investigation ────────────────────────────────
    investigation = (
        db.query(AIInvestigationRun)
        .filter(
            AIInvestigationRun.exception_id == exception.id,
            AIInvestigationRun.status == InvestigationStatus.COMPLETED,
        )
        .order_by(AIInvestigationRun.completed_at.desc())
        .first()
    )

    # Extract investigation signals (or use defaults if no investigation)
    if investigation and investigation.final_result:
        result = investigation.final_result
        confidence = investigation.final_confidence or 0.5
        root_cause = result.get("root_cause", "UNKNOWN")
        contradiction = result.get("contradiction_detected", False)
        evidence_ids = result.get("evidence_ids", [])
        uncertainties = result.get("uncertainties", [])
        requires_human = investigation.requires_human
    else:
        confidence = 0.3
        root_cause = "UNKNOWN"
        contradiction = False
        evidence_ids = []
        uncertainties = ["No AI investigation available"]
        requires_human = True

    # ── 2. ML signals ─────────────────────────────────────────────────────────
    from app.models.ml_prediction import MLPrediction
    ml_pred = (
        db.query(MLPrediction)
        .filter(
            MLPrediction.entity_type == "exception",
            MLPrediction.entity_id == str(exception.id),
        )
        .order_by(MLPrediction.created_at.desc())
        .first()
    )
    ml_confidence = ml_pred.confidence if ml_pred else None
    ml_agrees = (
        ml_pred.prediction == root_cause
        if ml_pred else True  # No ML → no disagreement signal
    )

    # ── 3. Evidence quality ───────────────────────────────────────────────────
    evidence_count = len(evidence_ids) if evidence_ids else 0
    avg_trust = 0.7  # Default; in production this would be computed from evidence docs
    has_primary = evidence_count > 0

    # ── 4. Decision ───────────────────────────────────────────────────────────
    decision_result = decision_engine.make_decision(
        db=db,
        exception_type=exception.exception_type.value,
        root_cause=root_cause,
        confidence=confidence,
        amount=exception.amount,
        evidence_count=evidence_count,
        avg_trust=avg_trust,
        has_primary_evidence=has_primary,
        contradiction_detected=contradiction,
        uncertainty_count=len(uncertainties),
        requires_human=requires_human,
        ml_confidence=ml_confidence,
        ml_agrees_with_ai=ml_agrees,
        evidence_ids=evidence_ids,
    )

    # ── 5. Create decision record ─────────────────────────────────────────────
    ctrl_decision = ControllerDecision(
        controller_run_id=run.id,
        exception_id=exception.id,
        investigation_id=investigation.id if investigation else None,
        decision=ControllerDecisionType(decision_result.decision),
        action=decision_result.action,
        confidence=decision_result.confidence,
        risk_score=decision_result.risk_score,
        risk_band=decision_result.risk_band,
        reason=decision_result.reason,
        evidence_ids=decision_result.evidence_ids,
        policy_version=decision_result.policy_version,
        requires_approval=decision_result.requires_human_approval,
        status=ControllerDecisionStatus.PENDING,
        risk_details=decision_result.risk_details,
        dry_run=dry_run,
    )
    db.add(ctrl_decision)
    db.commit()
    db.refresh(ctrl_decision)

    AuditService(db).log(
        AuditAction.DECISION_CREATED,
        f"Decision: {decision_result.decision} for exception {exception.id} "
        f"(confidence={confidence:.0%}, risk={decision_result.risk_band.value})",
        user_id=user_id,
        merchant_id=merchant_id,
        entity_type="controller_decision",
        entity_id=str(ctrl_decision.id),
        metadata={
            "decision": decision_result.decision,
            "action": decision_result.action,
            "confidence": confidence,
            "risk_score": decision_result.risk_score,
            "risk_band": decision_result.risk_band.value,
            "policy_version": decision_result.policy_version,
            "dry_run": dry_run,
        },
    )

    # ── 6. Route decision ─────────────────────────────────────────────────────
    amount = exception.amount or Decimal("0")

    if decision_result.decision == "AUTO_EXECUTE":
        if dry_run:
            ctrl_decision.status = ControllerDecisionStatus.EXECUTED
            db.commit()
            run.auto_executed += 1
            run.amount_auto_resolved += amount
        else:
            result = execute_action(
                db=db,
                decision=ctrl_decision,
                action_type=decision_result.action or "MARK_EXCEPTION_RESOLVED",
                exception_id=exception.id,
                executed_by="controller",
                merchant_id=merchant_id,
                dry_run=False,
            )
            ctrl_decision.status = ControllerDecisionStatus.EXECUTED
            db.commit()
            run.auto_executed += 1
            run.amount_auto_resolved += amount

    elif decision_result.decision == "RECOMMEND":
        create_approval_request(db, ctrl_decision, merchant_id)
        run.recommended += 1
        run.amount_awaiting_review += amount

    elif decision_result.decision == "ESCALATE":
        escalate_decision(db, ctrl_decision, merchant_id)
        run.escalated += 1
        run.amount_escalated += amount

    elif decision_result.decision == "BLOCK":
        block_decision(db, ctrl_decision, merchant_id)
        run.blocked += 1

    run.processed += 1
    run.amount_processed += amount
    db.commit()


def _finalize_run(
    db: Session,
    run: ControllerRun,
    user_id: Optional[uuid.UUID],
    merchant_id: Optional[uuid.UUID],
) -> None:
    """Finalize the controller run with final status and audit."""
    if run.failed > 0 and run.processed < run.total_exceptions:
        run.status = ControllerRunStatus.PARTIAL
    elif run.failed > 0:
        run.status = ControllerRunStatus.PARTIAL
    else:
        run.status = ControllerRunStatus.COMPLETED
    run.completed_at = datetime.now(timezone.utc)
    db.commit()

    AuditService(db).log(
        AuditAction.CONTROLLER_RUN_COMPLETED,
        f"Controller run completed: {run.processed}/{run.total_exceptions} processed, "
        f"auto={run.auto_executed} review={run.recommended} "
        f"escalated={run.escalated} blocked={run.blocked} failed={run.failed}",
        user_id=user_id,
        merchant_id=merchant_id,
        entity_type="controller_run",
        entity_id=str(run.id),
        metadata={
            "total": run.total_exceptions,
            "processed": run.processed,
            "auto_executed": run.auto_executed,
            "recommended": run.recommended,
            "escalated": run.escalated,
            "blocked": run.blocked,
            "failed": run.failed,
            "amount_processed": float(run.amount_processed),
            "amount_auto_resolved": float(run.amount_auto_resolved),
            "dry_run": run.dry_run,
        },
    )

    logger.info(
        "Controller run %s completed: %d/%d processed "
        "(auto=%d review=%d escalated=%d blocked=%d failed=%d)",
        run.id, run.processed, run.total_exceptions,
        run.auto_executed, run.recommended, run.escalated, run.blocked, run.failed,
    )


def get_controller_metrics(db: Session, merchant_id: Optional[uuid.UUID] = None) -> dict:
    """Compute controller metrics for the dashboard."""
    from sqlalchemy import func

    query = db.query(ControllerRun)
    if merchant_id:
        query = query.filter(ControllerRun.merchant_id == merchant_id)

    runs = query.all()

    total_processed = sum(r.processed for r in runs)
    total_auto = sum(r.auto_executed for r in runs)
    total_review = sum(r.recommended for r in runs)
    total_escalated = sum(r.escalated for r in runs)
    total_blocked = sum(r.blocked for r in runs)
    total_failed = sum(r.failed for r in runs)
    amount_processed = sum(float(r.amount_processed) for r in runs)
    amount_auto = sum(float(r.amount_auto_resolved) for r in runs)
    amount_review = sum(float(r.amount_awaiting_review) for r in runs)
    amount_escalated = sum(float(r.amount_escalated) for r in runs)

    return {
        "operational": {
            "total_runs": len(runs),
            "exceptions_processed": total_processed,
            "decisions_generated": total_processed,
            "actions_executed": total_auto,
            "actions_awaiting_approval": total_review,
            "escalations": total_escalated,
            "blocked": total_blocked,
            "failed": total_failed,
        },
        "financial": {
            "amount_processed": amount_processed,
            "amount_auto_resolved": amount_auto,
            "amount_under_review": amount_review,
            "amount_escalated": amount_escalated,
            "amount_blocked": 0,
        },
        "quality": {
            "auto_resolution_rate": total_auto / max(total_processed, 1),
            "human_review_rate": total_review / max(total_processed, 1),
            "escalation_rate": total_escalated / max(total_processed, 1),
            "failure_rate": total_failed / max(total_processed, 1),
            "block_rate": total_blocked / max(total_processed, 1),
        },
    }
