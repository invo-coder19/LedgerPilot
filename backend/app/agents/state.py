"""LangGraph investigation state.

InvestigationState is the single shared mutable object that flows through every
graph node. It is a TypedDict so LangGraph can serialise/deserialise it without
requiring a Pydantic model dependency in the graph core.

All fields are Optional so each node can safely read partial state.
"""

from __future__ import annotations

from typing import Any, Optional
from typing_extensions import TypedDict


class StepRecord(TypedDict):
    """A single recorded step within an investigation."""
    step_name: str
    tool_name: Optional[str]
    input_summary: str
    output_summary: str
    duration_ms: Optional[int]


class InvestigationState(TypedDict, total=False):
    # ── Inputs ────────────────────────────────────────────────────────────────
    exception_id: str
    merchant_id: Optional[str]

    # ── Loaded data ───────────────────────────────────────────────────────────
    exception_data: dict              # raw exception dict from DB
    intelligence_context: dict        # Phase 3A intelligence-context response

    # ── Investigation planning ────────────────────────────────────────────────
    investigation_plan: list[str]     # list of evidence types to fetch

    # ── Gathered evidence ─────────────────────────────────────────────────────
    evidence: list[dict]              # all retrieved evidence documents
    finance_rules: list[dict]
    historical_cases: list[dict]

    # ── ML signals ────────────────────────────────────────────────────────────
    ml_prediction: Optional[dict]     # Phase 3A classifier result
    anomaly_result: Optional[dict]    # Phase 3A anomaly result

    # ── Per-node findings (accumulated) ──────────────────────────────────────
    findings: list[str]

    # ── Structured result ─────────────────────────────────────────────────────
    root_cause: str                   # must be in ROOT_CAUSE_TAXONOMY
    raw_llm_confidence: float         # LLM self-reported confidence [0,1]
    confidence: float                 # policy-computed confidence [0,1]
    confidence_band: str              # HIGH / MEDIUM / LOW
    evidence_ids: list[str]
    uncertainties: list[str]
    requires_human_review: bool
    contradiction_detected: bool

    # ── Final structured output ───────────────────────────────────────────────
    final_result: Optional[dict]      # serialised InvestigationResult
    observed_facts: list[str]
    inferences: list[str]
    conclusion: str
    recommendation: str
    next_steps: list[str]

    # ── Investigation trace ───────────────────────────────────────────────────
    steps: list[StepRecord]

    # ── Error handling ────────────────────────────────────────────────────────
    error: Optional[str]
    llm_retry_count: int

    # ── Run metadata ──────────────────────────────────────────────────────────
    run_id: Optional[str]             # set by investigator.py after DB write
    model_provider: str
    model_name: str


ROOT_CAUSE_TAXONOMY = [
    "FEE_VARIANCE",
    "AMOUNT_MISMATCH",
    "DUPLICATE",
    "MISSING_INVOICE",
    "MISSING_SETTLEMENT",
    "REFUND_MISMATCH",
    "DATE_MISMATCH",
    "UNKNOWN",
]


def initial_state(exception_id: str, merchant_id: Optional[str] = None) -> InvestigationState:
    """Create a clean starting state for a new investigation."""
    return InvestigationState(
        exception_id=exception_id,
        merchant_id=merchant_id,
        exception_data={},
        intelligence_context={},
        investigation_plan=[],
        evidence=[],
        finance_rules=[],
        historical_cases=[],
        ml_prediction=None,
        anomaly_result=None,
        findings=[],
        root_cause="UNKNOWN",
        raw_llm_confidence=0.5,
        confidence=0.5,
        confidence_band="LOW",
        evidence_ids=[],
        uncertainties=[],
        requires_human_review=True,
        contradiction_detected=False,
        final_result=None,
        observed_facts=[],
        inferences=[],
        conclusion="",
        recommendation="",
        next_steps=[],
        steps=[],
        error=None,
        llm_retry_count=0,
        run_id=None,
        model_provider="",
        model_name="",
    )
