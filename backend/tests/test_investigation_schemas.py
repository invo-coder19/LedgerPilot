"""Tests for investigation Pydantic schemas — Phase 3B."""

import pytest
from pydantic import ValidationError

from app.schemas.investigation import (
    CopilotRequest,
    InvestigationResultSchema,
    InvestigationRunResponse,
    InvestigationStepResponse,
    StartInvestigationResponse,
)
from datetime import datetime
import uuid


# ── InvestigationResultSchema ─────────────────────────────────────────────────

class TestInvestigationResultSchema:
    def _valid(self, **kw) -> dict:
        defaults = dict(
            exception_id=str(uuid.uuid4()),
            root_cause="FEE_VARIANCE",
            confidence=0.90,
            confidence_band="HIGH",
            conclusion="Settlement differs due to processing fee.",
            observed_facts=["Payment: ₹10,000", "Settlement: ₹9,820"],
            inferences=["The ₹180 difference is likely a processing fee."],
            evidence_ids=["pay-001", "set-001"],
            recommendation="Verify the fee rate.",
            next_steps=["Check merchant agreement"],
            uncertainties=[],
            requires_human_review=False,
            contradiction_detected=False,
        )
        defaults.update(kw)
        return defaults

    def test_valid(self):
        schema = InvestigationResultSchema(**self._valid())
        assert schema.confidence == 0.90

    def test_confidence_too_high_rejected(self):
        with pytest.raises(ValidationError):
            InvestigationResultSchema(**self._valid(confidence=1.5))

    def test_confidence_negative_rejected(self):
        with pytest.raises(ValidationError):
            InvestigationResultSchema(**self._valid(confidence=-0.1))

    def test_all_root_causes_valid(self):
        root_causes = [
            "FEE_VARIANCE", "AMOUNT_MISMATCH", "DUPLICATE",
            "MISSING_INVOICE", "MISSING_SETTLEMENT",
            "REFUND_MISMATCH", "DATE_MISMATCH", "UNKNOWN",
        ]
        for rc in root_causes:
            schema = InvestigationResultSchema(**self._valid(root_cause=rc))
            assert schema.root_cause == rc

    def test_defaults_are_empty_lists(self):
        schema = InvestigationResultSchema(**self._valid())
        assert isinstance(schema.observed_facts, list)
        assert isinstance(schema.uncertainties, list)


# ── CopilotRequest ────────────────────────────────────────────────────────────

class TestCopilotRequest:
    def test_valid(self):
        req = CopilotRequest(question="What are the top exceptions?")
        assert req.question

    def test_empty_question_rejected(self):
        with pytest.raises(ValidationError):
            CopilotRequest(question="")

    def test_long_question_rejected(self):
        with pytest.raises(ValidationError):
            CopilotRequest(question="x" * 1001)


# ── StartInvestigationResponse ────────────────────────────────────────────────

class TestStartInvestigationResponse:
    def test_failed_response(self):
        resp = StartInvestigationResponse(
            investigation_id=str(uuid.uuid4()),
            status="FAILED",
            result=None,
            error="LLM unavailable",
            message="Investigation failed: LLM unavailable",
        )
        assert resp.result is None
        assert resp.error is not None

    def test_completed_response(self):
        resp = StartInvestigationResponse(
            investigation_id=str(uuid.uuid4()),
            status="COMPLETED",
            result={"root_cause": "FEE_VARIANCE", "confidence": 0.92},
            error=None,
            message="Investigation complete.",
        )
        assert resp.status == "COMPLETED"


# ── InvestigationStepResponse ─────────────────────────────────────────────────

class TestInvestigationStepResponse:
    def test_minimal(self):
        step = InvestigationStepResponse(
            id=str(uuid.uuid4()),
            step_name="load_exception",
            tool_name=None,
            input_summary=None,
            output_summary=None,
            duration_ms=None,
            created_at=datetime.utcnow(),
        )
        assert step.step_name == "load_exception"
        assert step.tool_name is None
