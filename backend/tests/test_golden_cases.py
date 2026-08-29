"""Golden test cases for the AI investigator — Phase 3B.

These tests run the full agent evaluation with the MockProvider.
No real API calls are made. Tests the deterministic policy layer.
"""

import pytest

from app.agents.evaluate import GOLDEN_CASES, evaluate_case


@pytest.mark.parametrize("case", GOLDEN_CASES, ids=[c.case_id for c in GOLDEN_CASES])
def test_golden_case_passes(case):
    """Every golden case must pass the evaluation criteria."""
    result = evaluate_case(case)
    assert result["passed"], (
        f"Golden case {case.case_id} failed:\n"
        f"  confidence={result['confidence']:.2f} "
        f"  (expected {case.expected_min_confidence:.2f}–{case.expected_max_confidence:.2f})\n"
        f"  human_review={result['requires_human_review']} "
        f"  (expected {case.expected_requires_human})"
    )


def test_fee_variance_high_confidence():
    """Case 1 (FEE_VARIANCE) should be HIGH or MEDIUM confidence."""
    case = next(c for c in GOLDEN_CASES if c.case_id == "CASE_1_FEE_VARIANCE")
    result = evaluate_case(case)
    assert result["confidence"] >= 0.70
    assert result["requires_human_review"] is False


def test_genuine_ambiguity_requires_human():
    """Case 4 (genuine ambiguity) must require human review."""
    case = next(c for c in GOLDEN_CASES if c.case_id == "CASE_4_GENUINE_AMBIGUITY")
    result = evaluate_case(case)
    assert result["requires_human_review"] is True
    assert result["confidence"] < 0.70


def test_conflicting_evidence_low_confidence():
    """Case 5 (conflicting evidence) must be low confidence with human review."""
    case = next(c for c in GOLDEN_CASES if c.case_id == "CASE_5_CONFLICTING_EVIDENCE")
    result = evaluate_case(case)
    assert result["requires_human_review"] is True
    assert result["confidence"] < 0.70


def test_root_causes_in_taxonomy():
    """All golden case expected root causes must be in the taxonomy."""
    from app.agents.state import ROOT_CAUSE_TAXONOMY
    for case in GOLDEN_CASES:
        assert case.expected_root_cause in ROOT_CAUSE_TAXONOMY, (
            f"{case.case_id}: {case.expected_root_cause} not in taxonomy"
        )


def test_confidence_always_in_bounds():
    """Confidence must always be [0, 1] for all golden cases."""
    for case in GOLDEN_CASES:
        result = evaluate_case(case)
        assert 0.0 <= result["confidence"] <= 1.0, (
            f"{case.case_id}: confidence {result['confidence']} out of bounds"
        )


def test_band_always_valid():
    """Confidence band must always be HIGH / MEDIUM / LOW."""
    for case in GOLDEN_CASES:
        result = evaluate_case(case)
        assert result["confidence_band"] in ("HIGH", "MEDIUM", "LOW"), (
            f"{case.case_id}: invalid band {result['confidence_band']}"
        )
