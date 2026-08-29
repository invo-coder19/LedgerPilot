"""XGBoost multi-class exception classifier.

Target classes (9):
  NORMAL              — No exception, record reconciles cleanly
  FEE_VARIANCE        — Fee charged differs from expected
  AMOUNT_MISMATCH     — Settlement or payment amount differs from invoice
  MISSING_INVOICE     — Payment has no matching invoice
  MISSING_SETTLEMENT  — Successful payment was not settled
  DUPLICATE           — Duplicate payment or settlement reference
  REFUND_MISMATCH     — Refund amount inconsistent with original
  DATE_MISMATCH       — Settlement date far outside expected window
  UNKNOWN             — Cannot classify with confidence

The classifier outputs a predicted class + per-class probability vector.
The confidence = probability of the predicted class.
"""

from __future__ import annotations

import numpy as np
from sklearn.preprocessing import LabelEncoder, StandardScaler
from xgboost import XGBClassifier

EXCEPTION_CLASSES: list[str] = [
    "NORMAL",
    "FEE_VARIANCE",
    "AMOUNT_MISMATCH",
    "MISSING_INVOICE",
    "MISSING_SETTLEMENT",
    "DUPLICATE",
    "REFUND_MISMATCH",
    "DATE_MISMATCH",
    "UNKNOWN",
]

_N_CLASSES = len(EXCEPTION_CLASSES)


class ExceptionClassifier:
    """XGBoost-based exception type classifier."""

    MODEL_VERSION = "v1"
    TOP_K_ALTERNATIVES = 3

    def __init__(self, random_seed: int = 42) -> None:
        self.scaler = StandardScaler()
        self.label_encoder = LabelEncoder()
        self.label_encoder.classes_ = np.array(EXCEPTION_CLASSES)
        self.model = XGBClassifier(
            n_estimators=300,
            max_depth=6,
            learning_rate=0.1,
            subsample=0.8,
            colsample_bytree=0.8,
            use_label_encoder=False,
            eval_metric="mlogloss",
            random_state=random_seed,
            n_jobs=-1,
            verbosity=0,
        )
        self._is_fitted = False

    # ── Training ──────────────────────────────────────────────────────────────

    def fit(
        self,
        X: np.ndarray,
        y_labels: list[str],
        X_val: np.ndarray | None = None,
        y_val: list[str] | None = None,
    ) -> "ExceptionClassifier":
        """Fit scaler and XGBoost classifier.

        Parameters
        ----------
        X        : Training feature array (n_samples, n_features)
        y_labels : String class labels for each training sample
        X_val    : Optional validation features for early stopping
        y_val    : Optional validation labels
        """
        self.label_encoder.fit(y_labels)
        y_encoded = self.label_encoder.transform(y_labels)

        X_scaled = self.scaler.fit_transform(X)

        fit_kwargs: dict = {}
        if X_val is not None and y_val is not None:
            y_val_encoded = self.label_encoder.transform(y_val)
            X_val_scaled = self.scaler.transform(X_val)
            fit_kwargs["eval_set"] = [(X_val_scaled, y_val_encoded)]
            fit_kwargs["verbose"] = False

        self.model.fit(X_scaled, y_encoded, **fit_kwargs)
        self._is_fitted = True
        return self

    # ── Inference ─────────────────────────────────────────────────────────────

    def predict(self, X: np.ndarray) -> list[dict]:
        """Return predictions for each sample.

        Returns
        -------
        list of dicts, each containing:
          predicted_type  : str
          confidence      : float  (probability of predicted class, in [0,1])
          top_alternatives: list of {"label": str, "confidence": float}
        """
        self._check_fitted()
        X_scaled = self.scaler.transform(X)
        proba = self.model.predict_proba(X_scaled)  # shape (n, n_classes)

        results = []
        for prob_row in proba:
            top_idx = int(np.argmax(prob_row))
            predicted_type = self.label_encoder.classes_[top_idx]
            confidence = float(round(prob_row[top_idx], 4))

            # Top-K alternatives (excluding the top prediction)
            sorted_idx = np.argsort(prob_row)[::-1]
            alternatives = []
            for idx in sorted_idx[1: self.TOP_K_ALTERNATIVES + 1]:
                alternatives.append({
                    "label": self.label_encoder.classes_[idx],
                    "confidence": float(round(prob_row[idx], 4)),
                })

            results.append({
                "predicted_type": predicted_type,
                "confidence": confidence,
                "top_alternatives": alternatives,
            })
        return results

    def predict_single(self, x: np.ndarray) -> dict:
        """Predict for a single feature vector (1-D array)."""
        return self.predict(x.reshape(1, -1))[0]

    def _check_fitted(self) -> None:
        if not self._is_fitted:
            raise RuntimeError(
                "ExceptionClassifier has not been fitted. "
                "Call fit() or load a saved model first."
            )
