"""Failure injection utilities.

These functions safely inject faults into the synthetic test environment.
CRITICAL: Only operates on synthetic/demo data. Never modifies production data.

Every injector function:
  1. Documents what it changes
  2. Returns a cleanup function to restore state
  3. Operates within a transaction that can be rolled back
"""

from __future__ import annotations

import logging
import uuid
from contextlib import contextmanager
from typing import Callable, Optional
from unittest.mock import MagicMock, patch

from sqlalchemy.orm import Session

logger = logging.getLogger("ledgerpilot.simulation")


@contextmanager
def inject_missing_bank_record(db: Session, bank_transaction_id: str):
    """Temporarily remove a bank record to simulate missing evidence."""
    from app.models.bank_transaction import BankTransaction

    record = db.get(BankTransaction, uuid.UUID(bank_transaction_id))
    original_status = None

    if record and hasattr(record, "is_active"):
        original_status = record.is_active
        record.is_active = False
        db.commit()
        logger.info("Injected: bank record %s deactivated", bank_transaction_id)

    try:
        yield {"injected": "bank_record_missing", "record_id": bank_transaction_id}
    finally:
        if record and original_status is not None:
            record.is_active = original_status
            db.commit()
            logger.info("Restored: bank record %s re-activated", bank_transaction_id)


@contextmanager
def inject_contradictory_bank_amount(db: Session, bank_transaction_id: str, wrong_amount: float):
    """Set a bank record amount to a contradictory value."""
    from app.models.bank_transaction import BankTransaction

    record = db.get(BankTransaction, uuid.UUID(bank_transaction_id))
    original_amount = None

    if record:
        original_amount = record.amount
        record.amount = wrong_amount
        db.commit()
        logger.info("Injected: bank record %s amount changed to %s", bank_transaction_id, wrong_amount)

    try:
        yield {"injected": "contradictory_amount", "original": original_amount, "injected_amount": wrong_amount}
    finally:
        if record and original_amount is not None:
            record.amount = original_amount
            db.commit()
            logger.info("Restored: bank record %s amount restored to %s", bank_transaction_id, original_amount)


@contextmanager
def inject_llm_failure(error_type: str = "timeout"):
    """Simulate LLM API failure."""
    from app.agents import graph as agent_graph_module

    error_messages = {
        "timeout": "LLM request timed out after 30s",
        "rate_limit": "LLM rate limit exceeded (429)",
        "unavailable": "LLM API unavailable (503)",
        "malformed": "LLM returned malformed/unparseable response",
    }
    error_msg = error_messages.get(error_type, "LLM error")

    def _failing_llm(*args, **kwargs):
        raise RuntimeError(f"[SIMULATED] {error_msg}")

    logger.info("Injected: LLM failure (%s)", error_type)

    # Patch the LLM client in the agent module
    with patch("langchain_google_genai.ChatGoogleGenerativeAI.__init__", side_effect=_failing_llm):
        with patch("langchain_openai.ChatOpenAI.__init__", side_effect=_failing_llm):
            yield {"injected": "llm_failure", "error_type": error_type}

    logger.info("Restored: LLM failure injection removed")


@contextmanager
def inject_ml_model_missing():
    """Simulate ML model artifact not found."""
    import os
    from app.core.config import get_settings

    settings = get_settings()
    classifier_path = settings.models_path / "exception_classifier.joblib"
    backup_path = settings.models_path / "exception_classifier.joblib.bak"

    renamed = False
    if classifier_path.exists():
        classifier_path.rename(backup_path)
        renamed = True
        logger.info("Injected: ML model artifact temporarily renamed")

    try:
        yield {"injected": "ml_model_missing", "path": str(classifier_path)}
    finally:
        if renamed and backup_path.exists():
            backup_path.rename(classifier_path)
            logger.info("Restored: ML model artifact restored")


@contextmanager
def inject_action_failure():
    """Simulate a database error during action execution."""
    from sqlalchemy.exc import OperationalError

    def _failing_commit(self):
        raise OperationalError("statement", {}, "[SIMULATED] DB error during commit")

    logger.info("Injected: action execution failure (DB error)")

    # Patch the session commit to fail exactly once
    call_count = {"n": 0}
    original_commit = Session.commit

    def _patched_commit(self):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise OperationalError("statement", {}, "[SIMULATED] DB error during action commit")
        return original_commit(self)

    with patch.object(Session, "commit", _patched_commit):
        yield {"injected": "action_failure", "error": "DB error on first commit"}

    logger.info("Restored: action failure injection removed")


@contextmanager
def inject_kill_switch(db: Session):
    """Activate the kill switch for the duration of the simulation."""
    from app.models.controller import ControllerConfig
    from datetime import datetime, timezone

    cfg = db.query(ControllerConfig).filter(ControllerConfig.key == "kill_switch").first()
    was_enabled = False

    if cfg:
        was_enabled = cfg.value.get("enabled", False)
        cfg.value = {"enabled": True}
    else:
        cfg = ControllerConfig(key="kill_switch", value={"enabled": True})
        db.add(cfg)

    db.commit()
    logger.info("Injected: kill switch ENABLED")

    try:
        yield {"injected": "kill_switch", "was_enabled": was_enabled}
    finally:
        if cfg:
            cfg.value = {"enabled": was_enabled}
            db.commit()
        logger.info("Restored: kill switch set back to %s", was_enabled)


@contextmanager
def inject_policy_missing(db: Session):
    """Deactivate all policies to simulate policy failure."""
    from app.models.controller import ControllerPolicy, PolicyStatus

    policies = db.query(ControllerPolicy).filter(ControllerPolicy.status == PolicyStatus.ACTIVE).all()
    for p in policies:
        p.status = PolicyStatus.INACTIVE
    db.commit()
    logger.info("Injected: %d policies deactivated", len(policies))

    try:
        yield {"injected": "policy_missing", "deactivated_count": len(policies)}
    finally:
        for p in policies:
            p.status = PolicyStatus.ACTIVE
        db.commit()
        logger.info("Restored: %d policies reactivated", len(policies))
