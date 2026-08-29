"""LangGraph node implementations for the investigation graph.

Each node is a pure function: (state) -> partial_state_update

Nodes:
  load_exception_node
  load_intelligence_context_node
  plan_investigation_node
  retrieve_targeted_evidence_node
  analyze_records_node
  check_ml_signals_node
  check_finance_rules_node
  compare_historical_cases_node
  determine_root_cause_node
  calculate_confidence_node
  validate_decision_node
  generate_explanation_node
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

from app.agents.policies import (
    compute_confidence,
    detect_contradiction,
    should_require_human_review,
)
from app.agents.prompts import (
    ANALYSIS_SYSTEM,
    ANALYSIS_USER,
    EXPLANATION_SYSTEM,
    EXPLANATION_USER,
    PLANNING_SYSTEM,
    PLANNING_USER,
    ROOT_CAUSE_SYSTEM,
    ROOT_CAUSE_USER,
)
from app.agents.state import InvestigationState, ROOT_CAUSE_TAXONOMY, StepRecord

logger = logging.getLogger(__name__)

_MAX_EVIDENCE_CHARS = 6000  # keep LLM context manageable


def _step(state: InvestigationState, name: str, tool: str | None, input_s: str, output_s: str, ms: int = 0) -> list[StepRecord]:
    record: StepRecord = {
        "step_name": name,
        "tool_name": tool,
        "input_summary": input_s[:500],
        "output_summary": output_s[:500],
        "duration_ms": ms,
    }
    return state.get("steps", []) + [record]


def _truncate_evidence(evidence: list[dict], max_chars: int = _MAX_EVIDENCE_CHARS) -> str:
    """Build a compact text summary of evidence items within the char budget."""
    lines = []
    total = 0
    for i, ev in enumerate(evidence):
        line = f"[{ev.get('id', i)}] {ev.get('title', 'Untitled')} ({ev.get('source_type', '?')}): {ev.get('content', '')[:300]}"
        if total + len(line) > max_chars:
            lines.append("... (remaining evidence truncated)")
            break
        lines.append(line)
        total += len(line)
    return "\n".join(lines) or "No evidence available."


def _safe_json_field(data: Any, field: str, default: Any = None) -> Any:
    if isinstance(data, dict):
        return data.get(field, default)
    return default


# ── Nodes ─────────────────────────────────────────────────────────────────────

def load_exception_node(state: InvestigationState, tools) -> dict:
    """Node 1: Load exception from database."""
    t0 = time.monotonic()
    exc_id = state["exception_id"]
    exc = tools.get_exception(exc_id)
    ms = int((time.monotonic() - t0) * 1000)

    if "error" in exc:
        return {
            "error": exc["error"],
            "steps": _step(state, "load_exception", "get_exception", exc_id, f"ERROR: {exc['error']}", ms),
        }

    return {
        "exception_data": exc,
        "steps": _step(state, "load_exception", "get_exception", exc_id,
                       f"{exc.get('exception_type')} {exc.get('severity')} amount={exc.get('amount')}", ms),
    }


def load_intelligence_context_node(state: InvestigationState, tools) -> dict:
    """Node 2: Load Phase 3A ML predictions from the ML prediction repo."""
    t0 = time.monotonic()
    exc_id = state["exception_id"]
    ml = tools.get_ml_prediction("exception", exc_id)
    ms = int((time.monotonic() - t0) * 1000)

    ctx = {"ml_prediction": ml if ml.get("available") else None}
    return {
        **ctx,
        "intelligence_context": ml,
        "steps": _step(state, "load_intelligence_context", "get_ml_prediction", exc_id,
                       f"ML available: {ml.get('available')}", ms),
    }


def plan_investigation_node(state: InvestigationState, provider) -> dict:
    """Node 3: Plan what evidence to collect — uses LLM."""
    t0 = time.monotonic()
    exc = state.get("exception_data", {})

    user_msg = PLANNING_USER.format(
        exception_type=exc.get("exception_type", "UNKNOWN"),
        severity=exc.get("severity", "UNKNOWN"),
        description=exc.get("description", "No description")[:300],
        source_type=exc.get("source_type", "?"),
        source_id=exc.get("source_id", "?"),
        amount=exc.get("amount", "N/A"),
    )

    try:
        result = provider.complete_structured(PLANNING_SYSTEM, user_msg)
        plan = result.get("evidence_needed", ["TRANSACTION", "SETTLEMENT", "FINANCE_RULE"])
    except Exception as exc_err:
        logger.warning("Planning LLM call failed: %s", exc_err)
        # Fallback to type-based plan
        exc_type = exc.get("exception_type", "")
        plan = _fallback_plan(exc_type)

    ms = int((time.monotonic() - t0) * 1000)
    return {
        "investigation_plan": plan,
        "steps": _step(state, "plan_investigation", None, exc.get("exception_type", ""), str(plan), ms),
    }


def _fallback_plan(exception_type: str) -> list[str]:
    plans = {
        "AMOUNT_MISMATCH": ["TRANSACTION", "SETTLEMENT", "FINANCE_RULE", "HISTORICAL_CASE"],
        "FEE_VARIANCE": ["TRANSACTION", "SETTLEMENT", "FINANCE_RULE"],
        "MISSING_INVOICE": ["TRANSACTION", "INVOICE", "HISTORICAL_CASE"],
        "MISSING_SETTLEMENT": ["TRANSACTION", "SETTLEMENT", "FINANCE_RULE", "HISTORICAL_CASE"],
        "DUPLICATE": ["TRANSACTION", "SETTLEMENT", "HISTORICAL_CASE"],
        "REFUND_MISMATCH": ["TRANSACTION", "SETTLEMENT", "INVOICE", "HISTORICAL_CASE"],
        "DATE_MISMATCH": ["TRANSACTION", "SETTLEMENT", "FINANCE_RULE"],
    }
    return plans.get(exception_type, ["TRANSACTION", "SETTLEMENT", "FINANCE_RULE", "HISTORICAL_CASE"])


def retrieve_targeted_evidence_node(state: InvestigationState, tools) -> dict:
    """Node 4: Retrieve evidence documents based on the investigation plan."""
    t0 = time.monotonic()
    exc = state.get("exception_data", {})
    plan = state.get("investigation_plan", [])
    description = exc.get("description", "financial exception")
    source_id = exc.get("source_id", "")

    # Filter plan to valid source types
    valid_types = {"TRANSACTION", "SETTLEMENT", "INVOICE", "BANK_TRANSACTION",
                   "FINANCE_RULE", "HISTORICAL_CASE"}
    source_types = [t for t in plan if t in valid_types and t not in ("FINANCE_RULE", "HISTORICAL_CASE")]

    evidence = tools.search_evidence(
        query=f"{description} {source_id}",
        top_k=12,
        source_types=source_types if source_types else None,
    )
    ms = int((time.monotonic() - t0) * 1000)

    return {
        "evidence": evidence,
        "steps": _step(state, "retrieve_evidence", "search_evidence",
                       f"plan={plan}", f"{len(evidence)} docs retrieved", ms),
    }


def analyze_records_node(state: InvestigationState, provider) -> dict:
    """Node 5: Analyze retrieved records — uses LLM."""
    t0 = time.monotonic()
    exc = state.get("exception_data", {})
    ml = state.get("ml_prediction") or {}
    evidence = state.get("evidence", [])

    exc_summary = (
        f"Type: {exc.get('exception_type')} | Severity: {exc.get('severity')} | "
        f"Amount: {exc.get('amount')} | {exc.get('description', '')[:200]}"
    )
    ml_summary = (
        f"Predicted: {ml.get('predicted_type', 'N/A')} "
        f"(confidence: {ml.get('confidence', 'N/A')})"
        if ml.get("available") else "ML analysis not available"
    )

    user_msg = ANALYSIS_USER.format(
        exception_summary=exc_summary,
        ml_summary=ml_summary,
        evidence_summary=_truncate_evidence(evidence),
    )

    try:
        result = provider.complete_structured(ANALYSIS_SYSTEM, user_msg)
        findings = result.get("findings", [])
        observed_facts = result.get("observed_facts", [])
    except Exception as err:
        logger.warning("Analysis LLM call failed: %s", err)
        findings = [f"Analysis failed: {str(err)[:100]}"]
        observed_facts = []

    ms = int((time.monotonic() - t0) * 1000)
    return {
        "findings": findings,
        "observed_facts": observed_facts,
        "steps": _step(state, "analyze_records", None, f"{len(evidence)} evidence docs",
                       f"{len(findings)} findings", ms),
    }


def check_ml_signals_node(state: InvestigationState, tools) -> dict:
    """Node 6: Deterministic ML signal check — no LLM needed."""
    t0 = time.monotonic()
    exc = state.get("exception_data", {})
    exc_id = state.get("exception_id", "")

    ml_pred = tools.get_ml_prediction("exception", exc_id)
    findings = list(state.get("findings", []))

    if ml_pred.get("available"):
        findings.append(
            f"ML classifier: {ml_pred.get('predicted_type')} "
            f"(confidence {float(ml_pred.get('confidence', 0)):.0%})"
        )
    else:
        findings.append("ML prediction not available — models may not be trained")

    ms = int((time.monotonic() - t0) * 1000)
    return {
        "ml_prediction": ml_pred if ml_pred.get("available") else None,
        "findings": findings,
        "steps": _step(state, "check_ml_signals", "get_ml_prediction", exc_id,
                       ml_pred.get("predicted_type", "unavailable"), ms),
    }


def check_finance_rules_node(state: InvestigationState, tools) -> dict:
    """Node 7: Retrieve relevant finance rules from RAG."""
    t0 = time.monotonic()
    exc = state.get("exception_data", {})
    query = f"{exc.get('exception_type', '')} {exc.get('description', '')[:200]}"
    rules = tools.get_finance_rules(query)
    ms = int((time.monotonic() - t0) * 1000)
    return {
        "finance_rules": rules,
        "steps": _step(state, "check_finance_rules", "get_finance_rules", query,
                       f"{len(rules)} rules retrieved", ms),
    }


def compare_historical_cases_node(state: InvestigationState, tools) -> dict:
    """Node 8: Retrieve similar historical cases from RAG."""
    t0 = time.monotonic()
    exc = state.get("exception_data", {})
    description = exc.get("description", "financial exception")
    cases = tools.get_similar_cases(description)
    ms = int((time.monotonic() - t0) * 1000)
    return {
        "historical_cases": cases,
        "steps": _step(state, "compare_historical_cases", "get_similar_cases", description[:100],
                       f"{len(cases)} cases retrieved", ms),
    }


def determine_root_cause_node(state: InvestigationState, provider) -> dict:
    """Node 9: Determine root cause — uses LLM."""
    t0 = time.monotonic()
    exc = state.get("exception_data", {})
    findings = state.get("findings", [])
    ml = state.get("ml_prediction") or {}
    rules = state.get("finance_rules", [])
    cases = state.get("historical_cases", [])

    exc_summary = (
        f"Type: {exc.get('exception_type')} | Amount: {exc.get('amount')} | "
        f"{exc.get('description', '')[:300]}"
    )
    ml_summary = (
        f"ML: {ml.get('predicted_type')} ({float(ml.get('confidence', 0)):.0%})"
        if ml else "ML: unavailable"
    )
    rules_summary = _truncate_evidence(rules, max_chars=2000)
    cases_summary = _truncate_evidence(cases, max_chars=2000)

    user_msg = ROOT_CAUSE_USER.format(
        exception_summary=exc_summary,
        findings="\n".join(f"- {f}" for f in findings),
        ml_summary=ml_summary,
        rules_summary=rules_summary,
        cases_summary=cases_summary,
    )

    retries = state.get("llm_retry_count", 0)
    root_cause = "UNKNOWN"
    raw_confidence = 0.5
    evidence_ids: list[str] = []
    uncertainties: list[str] = []
    requires_human = True

    for attempt in range(2):
        try:
            result = provider.complete_structured(ROOT_CAUSE_SYSTEM, user_msg)
            rc = result.get("root_cause", "UNKNOWN")
            # Validate root cause is in taxonomy
            if rc not in ROOT_CAUSE_TAXONOMY:
                rc = "UNKNOWN"
            root_cause = rc
            raw_confidence = float(result.get("confidence", 0.5))
            evidence_ids = result.get("evidence_ids", [])
            uncertainties = result.get("uncertainties", [])
            requires_human = result.get("requires_human_review", True)
            break
        except Exception as err:
            logger.warning("Root cause attempt %d failed: %s", attempt + 1, err)
            retries += 1

    ms = int((time.monotonic() - t0) * 1000)
    return {
        "root_cause": root_cause,
        "raw_llm_confidence": raw_confidence,
        "evidence_ids": evidence_ids,
        "uncertainties": uncertainties,
        "requires_human_review": requires_human,
        "llm_retry_count": retries,
        "steps": _step(state, "determine_root_cause", None, exc_summary[:150],
                       f"{root_cause} @ {raw_confidence:.0%}", ms),
    }


def calculate_confidence_node(state: InvestigationState) -> dict:
    """Node 10: Compute deterministic confidence score — no LLM."""
    t0 = time.monotonic()

    contradiction_detected = state.get("contradiction_detected", False)
    confidence, band, components = compute_confidence(
        evidence=state.get("evidence", []),
        finance_rules=state.get("finance_rules", []),
        historical_cases=state.get("historical_cases", []),
        ml_prediction=state.get("ml_prediction"),
        anomaly_result=state.get("anomaly_result"),
        root_cause=state.get("root_cause", "UNKNOWN"),
        llm_raw_confidence=state.get("raw_llm_confidence", 0.5),
        contradiction_detected=contradiction_detected,
    )

    requires_human = should_require_human_review(
        confidence=confidence,
        contradiction_detected=contradiction_detected,
        root_cause=state.get("root_cause", "UNKNOWN"),
        uncertainties=state.get("uncertainties", []),
    )

    ms = int((time.monotonic() - t0) * 1000)
    return {
        "confidence": confidence,
        "confidence_band": band,
        "requires_human_review": requires_human,
        "steps": _step(state, "calculate_confidence", None,
                       state.get("root_cause", "?"),
                       f"{confidence:.0%} {band}", ms),
    }


def validate_decision_node(state: InvestigationState) -> dict:
    """Node 11: Contradiction detection — deterministic."""
    t0 = time.monotonic()

    contradiction_detected, contradiction_msgs = detect_contradiction(
        evidence=state.get("evidence", []),
        ml_prediction=state.get("ml_prediction"),
        root_cause=state.get("root_cause", "UNKNOWN"),
        findings=state.get("findings", []),
    )

    uncertainties = list(state.get("uncertainties", []))
    if contradiction_msgs:
        uncertainties.extend(contradiction_msgs)

    ms = int((time.monotonic() - t0) * 1000)
    return {
        "contradiction_detected": contradiction_detected,
        "uncertainties": uncertainties,
        "steps": _step(state, "validate_decision", None,
                       state.get("root_cause", "?"),
                       f"contradictions={contradiction_detected} ({len(contradiction_msgs)})", ms),
    }


def generate_explanation_node(state: InvestigationState, provider) -> dict:
    """Node 12: Generate final human-readable explanation — uses LLM."""
    t0 = time.monotonic()

    exc = state.get("exception_data", {})
    exc_summary = (
        f"Type: {exc.get('exception_type')} | Amount: {exc.get('amount')} | "
        f"{exc.get('description', '')[:200]}"
    )
    user_msg = EXPLANATION_USER.format(
        exception_summary=exc_summary,
        root_cause=state.get("root_cause", "UNKNOWN"),
        confidence=f"{state.get('confidence', 0):.0%}",
        confidence_band=state.get("confidence_band", "LOW"),
        findings="\n".join(f"- {f}" for f in state.get("findings", [])),
        evidence_ids=", ".join(state.get("evidence_ids", [])) or "None",
        uncertainties="\n".join(f"- {u}" for u in state.get("uncertainties", [])) or "None",
        requires_human_review=state.get("requires_human_review", True),
    )

    conclusion = ""
    recommendation = ""
    next_steps: list[str] = []
    observed_facts = state.get("observed_facts", [])
    inferences: list[str] = []

    try:
        result = provider.complete_structured(EXPLANATION_SYSTEM, user_msg)
        conclusion = result.get("conclusion", "")
        recommendation = result.get("recommendation", "")
        next_steps = result.get("next_steps", [])
        observed_facts = result.get("observed_facts", observed_facts)
        inferences = result.get("inferences", [])
    except Exception as err:
        logger.warning("Explanation LLM call failed: %s", err)
        conclusion = f"Root cause: {state.get('root_cause')}. Confidence: {state.get('confidence', 0):.0%}."
        recommendation = "Manual review recommended."
        next_steps = ["Review the exception manually"]

    # Build final structured result
    final_result = {
        "exception_id": state.get("exception_id"),
        "root_cause": state.get("root_cause", "UNKNOWN"),
        "confidence": state.get("confidence", 0.0),
        "confidence_band": state.get("confidence_band", "LOW"),
        "conclusion": conclusion,
        "observed_facts": observed_facts,
        "inferences": inferences,
        "evidence_ids": state.get("evidence_ids", []),
        "recommendation": recommendation,
        "next_steps": next_steps,
        "uncertainties": state.get("uncertainties", []),
        "requires_human_review": state.get("requires_human_review", True),
        "contradiction_detected": state.get("contradiction_detected", False),
    }

    ms = int((time.monotonic() - t0) * 1000)
    return {
        "conclusion": conclusion,
        "recommendation": recommendation,
        "next_steps": next_steps,
        "inferences": inferences,
        "observed_facts": observed_facts,
        "final_result": final_result,
        "steps": _step(state, "generate_explanation", None,
                       state.get("root_cause", "?"), conclusion[:100], ms),
    }
