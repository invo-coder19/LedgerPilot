"""Tests for Phase 3A intelligence API routes.

These are integration tests that use the FastAPI test client.
They test authentication, route shapes, and graceful handling of
missing ML models.

We mock the embedding and ML inference services to avoid requiring
a live PostgreSQL database or trained models.
"""

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)


# ── Authentication tests ───────────────────────────────────────────────────────

class TestIntelligenceRouteAuth:
    def test_run_ml_requires_auth(self, client):
        resp = client.post(f"/api/v1/intelligence/exceptions/{uuid4()}/run-ml")
        assert resp.status_code == 403

    def test_intelligence_context_requires_auth(self, client):
        resp = client.get(f"/api/v1/intelligence/exceptions/{uuid4()}/intelligence-context")
        assert resp.status_code == 403

    def test_evidence_bundle_requires_auth(self, client):
        resp = client.get(f"/api/v1/intelligence/exceptions/{uuid4()}/evidence")
        assert resp.status_code == 403

    def test_evidence_search_requires_auth(self, client):
        resp = client.post("/api/v1/intelligence/evidence/search", json={"query": "test"})
        assert resp.status_code == 403


# ── Schema validation tests ───────────────────────────────────────────────────

class TestMLSchemas:
    def test_exception_prediction_confidence_bounds(self):
        from app.schemas.ml import ExceptionPredictionSchema
        from datetime import datetime
        # Valid
        pred = ExceptionPredictionSchema(
            id=str(uuid4()),
            predicted_type="AMOUNT_MISMATCH",
            confidence=0.85,
            model_version="v1",
            top_alternatives=[],
            created_at=datetime.utcnow(),
        )
        assert pred.confidence == 0.85

    def test_exception_prediction_confidence_out_of_range(self):
        from pydantic import ValidationError
        from app.schemas.ml import ExceptionPredictionSchema
        from datetime import datetime
        with pytest.raises(ValidationError):
            ExceptionPredictionSchema(
                id=str(uuid4()),
                predicted_type="NORMAL",
                confidence=1.5,  # invalid
                model_version="v1",
                top_alternatives=[],
                created_at=datetime.utcnow(),
            )

    def test_anomaly_prediction_score_bounds(self):
        from app.schemas.ml import AnomalyPredictionSchema
        from datetime import datetime
        pred = AnomalyPredictionSchema(
            id=str(uuid4()),
            is_anomaly=True,
            anomaly_score=0.92,
            model_version="v1",
            created_at=datetime.utcnow(),
        )
        assert 0.0 <= pred.anomaly_score <= 1.0

    def test_anomaly_prediction_negative_score_rejected(self):
        from pydantic import ValidationError
        from app.schemas.ml import AnomalyPredictionSchema
        from datetime import datetime
        with pytest.raises(ValidationError):
            AnomalyPredictionSchema(
                id=str(uuid4()),
                is_anomaly=False,
                anomaly_score=-0.1,  # invalid
                model_version="v1",
                created_at=datetime.utcnow(),
            )

    def test_ml_analysis_response_models_not_available(self):
        from app.schemas.ml import MLAnalysisResponse
        resp = MLAnalysisResponse(
            exception_id=str(uuid4()),
            classifier=None,
            anomaly=None,
            models_available=False,
            message="Models not trained.",
        )
        assert not resp.models_available
        assert resp.classifier is None
        assert resp.anomaly is None

    def test_evidence_search_request_min_length(self):
        from pydantic import ValidationError
        from app.schemas.ml import EvidenceSearchRequest
        with pytest.raises(ValidationError):
            EvidenceSearchRequest(query="")  # empty query rejected

    def test_evidence_search_request_top_k_bounds(self):
        from pydantic import ValidationError
        from app.schemas.ml import EvidenceSearchRequest
        with pytest.raises(ValidationError):
            EvidenceSearchRequest(query="test", top_k=25)  # max is 20

    def test_evidence_counts_defaults_to_zero(self):
        from app.schemas.ml import EvidenceCountsSchema
        counts = EvidenceCountsSchema()
        assert counts.total == 0
        assert counts.transactions == 0

    def test_intelligence_context_response_structure(self):
        from app.schemas.ml import IntelligenceContextResponse, EvidenceCountsSchema
        ctx = IntelligenceContextResponse(
            exception_id=str(uuid4()),
            deterministic_analysis={"exception_type": "AMOUNT_MISMATCH"},
            models_available=False,
            evidence=[],
            evidence_counts=EvidenceCountsSchema(),
        )
        assert ctx.phase_3b_ready is False
        assert ctx.ml_prediction is None
        assert ctx.anomaly_analysis is None


# ── Feature extraction edge cases (pure unit) ─────────────────────────────────

class TestFeatureEdgeCases:
    def test_settlement_delay_clamped_upper(self):
        from app.ml.features import extract_features
        from datetime import date, timedelta
        rec = {
            "transaction_date": date.today() - timedelta(days=400),
            "settlement_date": date.today(),
        }
        features = extract_features(rec)
        assert features["settlement_delay_days"] <= 365.0

    def test_settlement_delay_clamped_lower(self):
        from app.ml.features import extract_features
        from datetime import date, timedelta
        rec = {
            "transaction_date": date.today(),
            "settlement_date": date.today() - timedelta(days=60),
        }
        features = extract_features(rec)
        assert features["settlement_delay_days"] >= -30.0

    def test_tax_ratio_capped(self):
        from app.ml.features import extract_features
        # tax massively exceeds amount
        features = extract_features({"amount": 10, "tax": 10000})
        assert features["tax_ratio"] <= 1.0
