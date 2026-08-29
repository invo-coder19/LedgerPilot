"""Public investigator orchestration layer.

run_investigation() is the single entry point for starting an investigation.
It:
  1. Creates an AIInvestigationRun record (PENDING)
  2. Runs the LangGraph graph
  3. Persists each step
  4. Updates the run record to COMPLETED / FAILED
  5. Returns the final structured result

This design ensures Phase 4 can invoke investigations from background tasks
or queues without any API contract changes.
"""

from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.agents.graph import get_investigation_graph
from app.agents.state import InvestigationState, initial_state
from app.agents.tools import InvestigationTools
from app.core.config import get_settings
from app.models.audit_log import AuditAction
from app.models.investigation import AIInvestigationRun, AIInvestigationStep, InvestigationStatus
from app.services.audit_service import AuditService

logger = logging.getLogger(__name__)
settings = get_settings()


def run_investigation(
    db: Session,
    exception_id: str,
    merchant_id: Optional[uuid.UUID] = None,
    user_id: Optional[uuid.UUID] = None,
    provider_override: Optional[str] = None,
) -> dict:
    """Run a full investigation and return the result dict.

    This function is intentionally synchronous. Phase 4 can wrap it in
    a background task (Celery / FastAPI BackgroundTasks) without changes.

    Returns a dict with keys:
      investigation_id, status, result, error
    """
    t0 = time.monotonic()

    # ── Create run record ──────────────────────────────────────────────────────
    run = AIInvestigationRun(
        exception_id=uuid.UUID(exception_id),
        merchant_id=merchant_id,
        status=InvestigationStatus.RUNNING,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    run_id = str(run.id)

    # ── Audit log: started ─────────────────────────────────────────────────────
    audit = AuditService(db)
    audit.log(
        AuditAction.AI_INVESTIGATION_STARTED,
        f"AI investigation started for exception {exception_id}",
        user_id=user_id,
        merchant_id=merchant_id,
        entity_type="exception",
        entity_id=exception_id,
        metadata={"run_id": run_id},
    )

    # ── Build graph and tools ──────────────────────────────────────────────────
    tools = InvestigationTools(db=db, merchant_id=merchant_id)
    try:
        graph, provider = get_investigation_graph(tools, provider_override)
    except Exception as exc:
        return _fail(db, run, exc, run_id, user_id, merchant_id, exception_id, audit)

    run.model_provider = provider.provider_name
    run.model_name = provider.model_name
    run.model_version = "v1"
    db.commit()

    # ── Run graph ──────────────────────────────────────────────────────────────
    state = initial_state(exception_id, str(merchant_id) if merchant_id else None)
    state["run_id"] = run_id
    state["model_provider"] = provider.provider_name
    state["model_name"] = provider.model_name

    try:
        final_state: InvestigationState = graph.invoke(state)
    except Exception as exc:
        return _fail(db, run, exc, run_id, user_id, merchant_id, exception_id, audit)

    # ── Persist steps ──────────────────────────────────────────────────────────
    for step_record in final_state.get("steps", []):
        step = AIInvestigationStep(
            investigation_id=run.id,
            step_name=step_record.get("step_name", "unknown"),
            tool_name=step_record.get("tool_name"),
            input_summary=step_record.get("input_summary", "")[:2000],
            output_summary=step_record.get("output_summary", "")[:2000],
            duration_ms=step_record.get("duration_ms"),
        )
        db.add(step)

    # ── Update run record ──────────────────────────────────────────────────────
    duration_ms = int((time.monotonic() - t0) * 1000)
    final_result = final_state.get("final_result") or {}

    run.status = InvestigationStatus.COMPLETED
    run.completed_at = datetime.now(timezone.utc)
    run.final_result = final_result
    run.final_confidence = final_state.get("confidence")
    run.confidence_band = final_state.get("confidence_band")
    run.requires_human = final_state.get("requires_human_review", True)
    run.duration_ms = duration_ms
    db.commit()

    # ── Audit log: completed ───────────────────────────────────────────────────
    audit.log(
        AuditAction.AI_INVESTIGATION_COMPLETED,
        f"AI investigation completed: {final_state.get('root_cause')} "
        f"conf={final_state.get('confidence', 0):.0%} "
        f"human_review={final_state.get('requires_human_review')}",
        user_id=user_id,
        merchant_id=merchant_id,
        entity_type="investigation_run",
        entity_id=run_id,
        metadata={
            "root_cause": final_state.get("root_cause"),
            "confidence": final_state.get("confidence"),
            "confidence_band": final_state.get("confidence_band"),
            "requires_human": final_state.get("requires_human_review"),
            "duration_ms": duration_ms,
        },
    )

    logger.info(
        "Investigation %s completed: %s %.0f%% %s [%dms]",
        run_id,
        final_state.get("root_cause"),
        (final_state.get("confidence") or 0) * 100,
        final_state.get("confidence_band"),
        duration_ms,
    )

    return {
        "investigation_id": run_id,
        "status": "COMPLETED",
        "result": final_result,
        "error": None,
    }


def _fail(
    db: Session,
    run: AIInvestigationRun,
    exc: Exception,
    run_id: str,
    user_id: Optional[uuid.UUID],
    merchant_id: Optional[uuid.UUID],
    exception_id: str,
    audit: AuditService,
) -> dict:
    error_msg = str(exc)[:500]
    logger.error("Investigation %s failed: %s", run_id, exc, exc_info=True)
    try:
        run.status = InvestigationStatus.FAILED
        run.completed_at = datetime.now(timezone.utc)
        run.error_message = error_msg
        run.requires_human = True
        db.commit()

        audit.log(
            AuditAction.AI_INVESTIGATION_FAILED,
            f"AI investigation failed: {error_msg[:200]}",
            user_id=user_id,
            merchant_id=merchant_id,
            entity_type="exception",
            entity_id=exception_id,
            metadata={"run_id": run_id, "error": error_msg},
        )
    except Exception as inner:
        logger.error("Failed to record investigation failure: %s", inner)

    return {
        "investigation_id": run_id,
        "status": "FAILED",
        "result": None,
        "error": error_msg,
    }
