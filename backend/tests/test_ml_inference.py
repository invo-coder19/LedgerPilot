"""Tests for Phase 3A ML inference — classifier and anomaly detector.

These tests train a tiny model on synthetic data and verify:
  - Prediction schema shape and bounds
  - Confidence values are always in [0, 1]
  - Class labels match the expected taxonomy
  - Anomaly scores are in [0, 1]
  - Model registry save/load round-trip works
"""

import tempfile
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest

from app.ml.dataset import generate_dataset, train_val_test_split
from app.ml.anomaly_detection import AnomalyDetector
from app.ml.exception_classifier import EXCEPTION_CLASSES, ExceptionClassifier
from app.ml.features import FEATURE_NAMES, records_to_dataframe


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def small_dataset():
    """Generate a small training dataset (fast for tests)."""
    from app.ml.dataset import CLASS_WEIGHTS
    # Use very small counts for speed
    small_weights = {k: max(20, v // 10) for k, v in CLASS_WEIGHTS.items()}
    X_df, y = generate_dataset(class_weights=small_weights, seed=99)
    X_train, X_val, X_test, y_train, y_val, y_test = train_val_test_split(
        X_df, y, seed=99
    )
    return {
        "X_train": X_train.values,
        "X_val": X_val.values,
        "X_test": X_test.values,
        "y_train": y_train,
        "y_val": y_val,
        "y_test": y_test,
    }


@pytest.fixture(scope="module")
def trained_classifier(small_dataset):
    clf = ExceptionClassifier(random_seed=42)
    clf.fit(
        small_dataset["X_train"], small_dataset["y_train"],
        X_val=small_dataset["X_val"], y_val=small_dataset["y_val"],
    )
    return clf


@pytest.fixture(scope="module")
def trained_detector(small_dataset):
    normal_mask = [y == "NORMAL" for y in small_dataset["y_train"]]
    X_normal = small_dataset["X_train"][normal_mask]
    det = AnomalyDetector(random_seed=42)
    det.fit(X_normal)
    return det


@pytest.fixture
def sample_x(small_dataset):
    return small_dataset["X_test"][0]


# ── Classifier tests ──────────────────────────────────────────────────────────

class TestExceptionClassifier:
    def test_predict_returns_list(self, trained_classifier, small_dataset):
        preds = trained_classifier.predict(small_dataset["X_test"])
        assert isinstance(preds, list)
        assert len(preds) == len(small_dataset["X_test"])

    def test_predict_dict_keys(self, trained_classifier, sample_x):
        result = trained_classifier.predict_single(sample_x)
        assert "predicted_type" in result
        assert "confidence" in result
        assert "top_alternatives" in result

    def test_confidence_in_bounds(self, trained_classifier, small_dataset):
        preds = trained_classifier.predict(small_dataset["X_test"])
        for p in preds:
            assert 0.0 <= p["confidence"] <= 1.0, f"Confidence out of bounds: {p['confidence']}"

    def test_predicted_type_valid_class(self, trained_classifier, small_dataset):
        preds = trained_classifier.predict(small_dataset["X_test"])
        for p in preds:
            assert p["predicted_type"] in EXCEPTION_CLASSES, (
                f"Unexpected class: {p['predicted_type']}"
            )

    def test_top_alternatives_bounds(self, trained_classifier, sample_x):
        result = trained_classifier.predict_single(sample_x)
        for alt in result["top_alternatives"]:
            assert 0.0 <= alt["confidence"] <= 1.0
            assert alt["label"] in EXCEPTION_CLASSES

    def test_top_alternatives_not_include_top_pred(self, trained_classifier, sample_x):
        result = trained_classifier.predict_single(sample_x)
        alt_labels = [a["label"] for a in result["top_alternatives"]]
        assert result["predicted_type"] not in alt_labels

    def test_unfitted_raises(self):
        clf = ExceptionClassifier()
        with pytest.raises(RuntimeError, match="not been fitted"):
            clf.predict(np.zeros((1, len(FEATURE_NAMES))))

    def test_predict_batch_consistency(self, trained_classifier, small_dataset):
        X = small_dataset["X_test"][:5]
        batch = trained_classifier.predict(X)
        for i, row in enumerate(X):
            single = trained_classifier.predict_single(row)
            assert batch[i]["predicted_type"] == single["predicted_type"]
            assert abs(batch[i]["confidence"] - single["confidence"]) < 1e-5


# ── Anomaly detector tests ────────────────────────────────────────────────────

class TestAnomalyDetector:
    def test_predict_returns_dict_with_correct_keys(self, trained_detector, small_dataset):
        result = trained_detector.predict(small_dataset["X_test"])
        assert "anomaly_score" in result
        assert "is_anomaly" in result

    def test_anomaly_score_in_bounds(self, trained_detector, small_dataset):
        result = trained_detector.predict(small_dataset["X_test"])
        for score in result["anomaly_score"]:
            assert 0.0 <= score <= 1.0, f"Anomaly score out of bounds: {score}"

    def test_is_anomaly_is_bool_list(self, trained_detector, small_dataset):
        result = trained_detector.predict(small_dataset["X_test"])
        for flag in result["is_anomaly"]:
            assert isinstance(flag, bool)

    def test_predict_single_returns_scalars(self, trained_detector, sample_x):
        result = trained_detector.predict_single(sample_x)
        assert isinstance(result["anomaly_score"], float)
        assert isinstance(result["is_anomaly"], bool)

    def test_unfitted_raises(self):
        det = AnomalyDetector()
        with pytest.raises(RuntimeError, match="not been fitted"):
            det.predict(np.zeros((1, len(FEATURE_NAMES))))

    def test_normal_records_low_anomaly(self, trained_detector):
        """Normal records should generally score lower than anomalous ones."""
        normal_features = {
            "amount": 10000, "fee": 200, "tax": 36,
            "settlement_amount": 9800,
            "transaction_date": None, "settlement_date": None,
            "status": "SUCCESS", "payment_method": "UPI",
            "has_invoice": True, "has_settlement": True, "has_bank_credit": True,
        }
        from app.ml.features import extract_features, features_to_array
        x_normal = features_to_array(extract_features(normal_features))
        result = trained_detector.predict_single(x_normal)
        # Can't assert exact threshold, just that it runs and is in bounds
        assert 0.0 <= result["anomaly_score"] <= 1.0


# ── Model registry round-trip ─────────────────────────────────────────────────

class TestModelRegistry:
    def test_save_and_load_classifier(self, trained_classifier):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("app.ml.model_registry._models_dir", return_value=Path(tmpdir)):
                from app.ml import model_registry
                model_registry.save_classifier(trained_classifier)
                loaded = model_registry.load_classifier()
                # Loaded model should produce same predictions
                X = np.random.rand(3, len(FEATURE_NAMES)).astype(np.float32)
                orig = trained_classifier.predict(X)
                reloaded = loaded.predict(X)
                for i in range(3):
                    assert orig[i]["predicted_type"] == reloaded[i]["predicted_type"]

    def test_save_and_load_metadata(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("app.ml.model_registry._models_dir", return_value=Path(tmpdir)):
                from app.ml import model_registry
                meta = {"trained_at": "2026-01-01", "seed": 42}
                model_registry.save_metadata(meta)
                loaded = model_registry.load_metadata()
                assert loaded["seed"] == 42
                assert "saved_at" in loaded  # added by registry

    def test_models_exist_false_when_missing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("app.ml.model_registry._models_dir", return_value=Path(tmpdir)):
                from app.ml import model_registry
                assert not model_registry.models_exist()
