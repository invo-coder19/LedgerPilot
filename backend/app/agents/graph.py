"""LangGraph investigation graph.

Builds and compiles the StateGraph for the AI Finance Investigator.

The graph is built as a linear pipeline. Future phases can add conditional
edges (e.g. branch on uncertainty level, loop for additional evidence) without
modifying any node implementation.
"""

from __future__ import annotations

import functools
import logging
from typing import Optional

from langgraph.graph import END, START, StateGraph

from app.agents.nodes import (
    analyze_records_node,
    calculate_confidence_node,
    check_finance_rules_node,
    check_ml_signals_node,
    compare_historical_cases_node,
    determine_root_cause_node,
    generate_explanation_node,
    load_exception_node,
    load_intelligence_context_node,
    plan_investigation_node,
    retrieve_targeted_evidence_node,
    validate_decision_node,
)
from app.agents.provider import LLMProvider, get_provider
from app.agents.state import InvestigationState
from app.agents.tools import InvestigationTools

logger = logging.getLogger(__name__)


def _bind_tools(fn, tools):
    """Partially apply tools to a node function."""
    return functools.partial(fn, tools=tools)


def _bind_provider(fn, provider):
    """Partially apply provider to a node function."""
    return functools.partial(fn, provider=provider)


def _bind_both(fn, tools, provider):
    return functools.partial(fn, tools=tools, provider=provider)


def build_graph(tools: InvestigationTools, provider: LLMProvider) -> StateGraph:
    """Build the investigation graph with injected dependencies.

    Dependencies are injected at build time, not through LangGraph's
    tool-calling mechanism, so the agent remains framework-agnostic.
    """
    graph = StateGraph(InvestigationState)

    # ── Register nodes ─────────────────────────────────────────────────────────
    graph.add_node("load_exception",         _bind_tools(load_exception_node, tools))
    graph.add_node("load_intelligence",      _bind_tools(load_intelligence_context_node, tools))
    graph.add_node("plan_investigation",     _bind_provider(plan_investigation_node, provider))
    graph.add_node("retrieve_evidence",      _bind_tools(retrieve_targeted_evidence_node, tools))
    graph.add_node("analyze_records",        _bind_provider(analyze_records_node, provider))
    graph.add_node("check_ml_signals",       _bind_tools(check_ml_signals_node, tools))
    graph.add_node("check_finance_rules",    _bind_tools(check_finance_rules_node, tools))
    graph.add_node("compare_history",        _bind_tools(compare_historical_cases_node, tools))
    graph.add_node("determine_root_cause",   _bind_provider(determine_root_cause_node, provider))
    graph.add_node("validate_decision",      validate_decision_node)
    graph.add_node("calculate_confidence",   calculate_confidence_node)
    graph.add_node("generate_explanation",   _bind_provider(generate_explanation_node, provider))

    # ── Wire edges ─────────────────────────────────────────────────────────────
    graph.add_edge(START,                    "load_exception")
    graph.add_edge("load_exception",         "load_intelligence")
    graph.add_edge("load_intelligence",      "plan_investigation")
    graph.add_edge("plan_investigation",     "retrieve_evidence")
    graph.add_edge("retrieve_evidence",      "analyze_records")
    graph.add_edge("analyze_records",        "check_ml_signals")
    graph.add_edge("check_ml_signals",       "check_finance_rules")
    graph.add_edge("check_finance_rules",    "compare_history")
    graph.add_edge("compare_history",        "determine_root_cause")
    graph.add_edge("determine_root_cause",   "validate_decision")
    graph.add_edge("validate_decision",      "calculate_confidence")
    graph.add_edge("calculate_confidence",   "generate_explanation")
    graph.add_edge("generate_explanation",   END)

    return graph.compile()


def get_investigation_graph(
    tools: InvestigationTools,
    provider_override: Optional[str] = None,
):
    """Build and return a compiled investigation graph.

    Args:
        tools: Pre-instantiated InvestigationTools (merchant-scoped)
        provider_override: Optional provider name for testing
    """
    provider = get_provider(provider_override)
    return build_graph(tools, provider), provider
