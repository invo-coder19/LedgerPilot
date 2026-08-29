"""Anomaly detection using IsolationForest.

Score semantics
---------------
IsolationForest.decision_function returns values in (-inf, +inf) where
*more negative* = more anomalous.  We normalise this to [0, 1] where
  1.0 = highly anomalous
  0.0 = very normal

The normalisation uses a sigmoid-like mapping so scores are not
artificially boundary-clamped — they reflect genuine anomaly signal.

Do NOT interpret the score as a probability; it is an anomaly signal.
"""

from __future__ import annotations

import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

from app.ml.features import FEATURE_NAMES


class AnomalyDetector:
    """Wrapper around IsolationForest with score normalisation."""

    MODEL_VERSION = "v1"
    CONTAMINATION = 0.08  # Expected fraction of anomalies in training data

    def __init__(self, random_seed: int = 42) -> None:
        self.scaler = StandardScaler()
        self.model = IsolationForest(
            n_estimators=200,
            max_samples="auto",
            contamination=self.CONTAMINATION,
            random_state=random_seed,
            n_jobs=-1,
        )
        self._is_fitted = False

    # ── Training ──────────────────────────────────────────────────────────────

    def fit(self, X: np.ndarray) -> "AnomalyDetector":
        """Fit scaler and IsolationForest on training features.

        Parameters
        ----------
        X : np.ndarray, shape (n_samples, n_features)
            Training features — should NOT include labels.
        """
        X_scaled = self.scaler.fit_transform(X)
        self.model.fit(X_scaled)
        self._is_fitted = True
        return self

    # ── Inference ─────────────────────────────────────────────────────────────

    def predict(self, X: np.ndarray) -> dict[str, list]:
        """Return anomaly scores and flags for each sample.

        Returns
        -------
        dict with keys:
          anomaly_score : list[float]  — [0, 1], higher = more anomalous
          is_anomaly    : list[bool]   — True if IsolationForest predicts -1
        """
        self._check_fitted()
        X_scaled = self.scaler.transform(X)

        # decision_function: negative = anomalous, positive = normal
        raw_scores = self.model.decision_function(X_scaled)
        # Normalise: flip sign, then sigmoid squeeze to [0, 1]
        anomaly_scores = 1.0 / (1.0 + np.exp(raw_scores * 5))

        predictions = self.model.predict(X_scaled)  # 1 = normal, -1 = anomaly
        is_anomaly = [p == -1 for p in predictions]

        return {
            "anomaly_score": [float(round(s, 4)) for s in anomaly_scores],
            "is_anomaly": is_anomaly,
        }

    def predict_single(self, x: np.ndarray) -> dict[str, object]:
        """Predict for a single feature vector (1-D array)."""
        result = self.predict(x.reshape(1, -1))
        return {
            "anomaly_score": result["anomaly_score"][0],
            "is_anomaly": result["is_anomaly"][0],
        }

    def _check_fitted(self) -> None:
        if not self._is_fitted:
            raise RuntimeError(
                "AnomalyDetector has not been fitted. "
                "Call fit() or load a saved model first."
            )
