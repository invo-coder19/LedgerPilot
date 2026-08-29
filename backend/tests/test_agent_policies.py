"""Tests for confidence policy and contradiction detection."""

import pytest

from app.agents.policies import (
    classify_band,
    compute_confidence,
    compute_evidence_quality,
    compute_ml_support,
    detect_contradiction,
    is_safe_action,
    should_require_human_review,
)


# ── classify_band ──────────────────────────────────────────────────────────────

class TestClassifyBand:
    def test_high(self):
        assert classify_band(0.95) == "HIGH"
        assert classify_band(0.90) == "HIGH"

    def test_medium(self):
        assert classify_band(0.85) == "MEDIUM"
        assert classify_band(0.70) == "MEDIUM"

    def test_low(self):
        assert classify_band(0.69) == "LOW"
        assert classify_band(0.0) == "LOW"


# ── compute_evidence_quality ──────────────────────────────────────────────────

class TestEvidenceQuality:
    def test_empty_evidence(self):
        assert compute_evidence_quality([]) == 0.0

    def test_primary_evidence_scores_higher(self):
        primary = [{"trust_level": "PRIMARY"}, {"trust_level": "PRIMARY"}, {"trust_level": "PRIMARY"}]
        secondary = [{"trust_level": "SECONDARY"}, {"trust_level": "SECONDARY"}]
        assert compute_evidence_quality(primary) > compute_evidence_quality(secondary)

    def test_more_evidence_increases_quality(self):
        one = [{"trust_level": "PRIMARY"}]
        five = [{"trust_level": "PRIMARY"}] * 5
        assert compute_evidence_quality(five) > compute_evidence_quality(one)

    def test_capped_at_one(self):
        many = [{"trust_level": "PRIMARY"}] * 100
        assert compute_evidence_quality(many) <= 1.0


# ── compute_ml_support ────────────────────────────────────────────────────────

class TestMLSupport:
    def test_none_prediction_is_neutral(self):
        score = compute_ml_support(None, "FEE_VARIANCE")
        assert score == 0.5

    def test_matching_prediction_high_score(self):
        pred = {"predicted_type": "FEE_VARIANCE", "confidence": 0.95}
        score = compute_ml_support(pred, "FEE_VARIANCE")
        assert score == pytest.approx(0.95)

    def test_related_prediction_partial_credit(self):
        pred = {"predicted_type": "AMOUNT_MISMATCH", "confidence": 0.80}
        score = compute_ml_support(pred, "FEE_VARIANCE")
        assert 0.3 < score < 0.8

    def test_different_prediction_low_score(self):
        pred = {"predicted_type": "DUPLICATE", "confidence": 0.95}
        score = compute_ml_support(pred, "FEE_VARIANCE")
        assert score < 0.5


# ── compute_confidence ────────────────────────────────────────────────────────

class TestComputeConfidence:
    def _make_evidence(self, n=3):
        return [{"trust_level": "PRIMARY"} for _ in range(n)]

    def _make_rule(self, keyword="fee"):
        return [{"title": "Fee Rule", "content": f"Processing {keyword} rate deduction", "trust_level": "REFERENCE"}]

    def test_returns_float_in_bounds(self):
        conf, band, components = compute_confidence(
            evidence=[], finance_rules=[], historical_cases=[],
            ml_prediction=None, anomaly_result=None,
            root_cause="FEE_VARIANCE", llm_raw_confidence=0.5,
            contradiction_detected=False,
        )
        assert 0.0 <= conf <= 1.0
        assert band in ("HIGH", "MEDIUM", "LOW")

    def test_contradiction_caps_below_medium(self):
        conf, band, _ = compute_confidence(
            evidence=self._make_evidence(10),
            finance_rules=self._make_rule(),
            historical_cases=[],
            ml_prediction={"predicted_type": "FEE_VARIANCE", "confidence": 0.98},
            anomaly_result=None,
            root_cause="FEE_VARIANCE",
            llm_raw_confidence=0.98,
            contradiction_detected=True,
        )
        assert conf < 0.90
        assert band != "HIGH"

    def test_unknown_root_cause_capped(self):
        conf, band, _ = compute_confidence(
            evidence=self._make_evidence(10),
            finance_rules=self._make_rule(),
            historical_cases=[],
            ml_prediction={"predicted_type": "FEE_VARIANCE", "confidence": 0.90},
            anomaly_result=None,
            root_cause="UNKNOWN",
            llm_raw_confidence=0.90,
            contradiction_detected=False,
        )
        assert conf <= 0.65

    def test_strong_evidence_high_confidence(self):
        evidence = [{"trust_level": "PRIMARY"}] * 5
        rules = [{"title": "Fee Rule", "content": "fee processing rate deduction settlement", "trust_level": "REFERENCE"}]
        cases = [{"title": "Case 1", "content": "FEE_VARIANCE resolved", "trust_level": "HISTORICAL"}]
        ml = {"predicted_type": "FEE_VARIANCE", "confidence": 0.95}

        conf, band, _ = compute_confidence(
            evidence=evidence, finance_rules=rules, historical_cases=cases,
            ml_prediction=ml, anomaly_result=None, root_cause="FEE_VARIANCE",
            llm_raw_confidence=0.90, contradiction_detected=False,
        )
        assert conf > 0.60  # Should be reasonably high


# ── detect_contradiction ──────────────────────────────────────────────────────

class TestDetectContradiction:
    def test_no_contradiction_clean_case(self):
        ml = {"predicted_type": "FEE_VARIANCE", "confidence": 0.90}
        detected, msgs = detect_contradiction(
            evidence=[], ml_prediction=ml,
            root_cause="FEE_VARIANCE", findings=[],
        )
        assert not detected
        assert len(msgs) == 0

    def test_ml_contradiction_detected(self):
        ml = {"predicted_type": "DUPLICATE", "confidence": 0.85}
        detected, msgs = detect_contradiction(
            evidence=[], ml_prediction=ml,
            root_cause="FEE_VARIANCE", findings=[],
        )
        assert detected
        assert len(msgs) >= 1

    def test_low_ml_confidence_not_contradiction(self):
        ml = {"predicted_type": "DUPLICATE", "confidence": 0.60}
        detected, _ = detect_contradiction(
            evidence=[], ml_prediction=ml,
            root_cause="FEE_VARIANCE", findings=[],
        )
        assert not detected

    def test_finding_contradiction_keyword(self):
        detected, msgs = detect_contradiction(
            evidence=[], ml_prediction=None, root_cause="FEE_VARIANCE",
            findings=["Bank record does not match the proposed fee-variance hypothesis — contradicts the settlement"],
        )
        assert detected


# ── should_require_human_review ───────────────────────────────────────────────

class TestHumanReviewPolicy:
    def test_contradiction_requires_review(self):
        assert should_require_human_review(0.95, True, "FEE_VARIANCE", [])

    def test_low_confidence_requires_review(self):
        assert should_require_human_review(0.65, False, "FEE_VARIANCE", [])

    def test_unknown_requires_review(self):
        assert should_require_human_review(0.80, False, "UNKNOWN", [])

    def test_many_uncertainties_requires_review(self):
        assert should_require_human_review(0.80, False, "FEE_VARIANCE", ["u1", "u2", "u3"])

    def test_clean_case_no_review(self):
        assert not should_require_human_review(0.92, False, "FEE_VARIANCE", [])


# ── Safety boundary ───────────────────────────────────────────────────────────

class TestSafetyBoundary:
    def test_read_action_safe(self):
        assert is_safe_action("get_exception")
        assert is_safe_action("search_evidence")

    def test_write_actions_blocked(self):
        assert not is_safe_action("approve")
        assert not is_safe_action("refund")
        assert not is_safe_action("mark_reconciled")
        assert not is_safe_action("send_email")
