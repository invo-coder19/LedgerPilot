"""Celery tasks for the autonomous controller.

Tasks call reusable services — no business logic duplication.
All tasks check state before executing (idempotent).
"""

from __future__ import annotations

import logging
import uuid

from app.celery_app import celery_app
from app.core.database import SessionLocal

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="controller.run_batch", max_retries=2)
def run_controller_batch(
    self,
    merchant_id: str,
    reconciliation_run_id: str | None = None,
    dry_run: bool = False,
    user_id: str | None = None,
) -> dict:
    """Run the autonomous controller across all eligible exceptions.

    This task wraps controller_service.start_controller_run() for
    background execution via Celery.
    """
    from app.controller.controller_service import start_controller_run

    db = SessionLocal()
    try:
        run = start_controller_run(
            db=db,
            merchant_id=uuid.UUID(merchant_id),
            reconciliation_run_id=reconciliation_run_id,
            dry_run=dry_run,
            user_id=uuid.UUID(user_id) if user_id else None,
        )
        return {
            "controller_run_id": str(run.id),
            "status": run.status.value,
            "total_exceptions": run.total_exceptions,
            "processed": run.processed,
            "auto_executed": run.auto_executed,
            "recommended": run.recommended,
            "escalated": run.escalated,
            "blocked": run.blocked,
            "failed": run.failed,
        }
    except Exception as exc:
        logger.error("Controller batch task failed: %s", exc, exc_info=True)
        raise self.retry(exc=exc, countdown=60)
    finally:
        db.close()


@celery_app.task(bind=True, name="controller.execute_approved", max_retries=3)
def execute_approved_action(
    self,
    approval_id: str,
    user_id: str,
    user_role: str,
    merchant_id: str | None = None,
) -> dict:
    """Execute an approved action in the background."""
    from app.controller.approval_service import approve_request
    from app.models.user import Role

    db = SessionLocal()
    try:
        result = approve_request(
            db=db,
            approval_id=uuid.UUID(approval_id),
            user_id=uuid.UUID(user_id),
            user_role=Role(user_role),
            merchant_id=uuid.UUID(merchant_id) if merchant_id else None,
        )
        return {
            "action_result_id": str(result.id),
            "status": result.status.value,
            "action": result.action,
        }
    except Exception as exc:
        logger.error("Approved action task failed: %s", exc, exc_info=True)
        raise self.retry(exc=exc, countdown=30)
    finally:
        db.close()
