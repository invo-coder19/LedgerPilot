"""Evaluation pipeline for Phase 3A ML models.

Usage:
    python -m app.ml.evaluation

Evaluates ONLY on the held-out test split.
Outputs:
  - Classification report (precision, recall, F1 per class)
  - Confusion matrix
  - Anomaly detector evaluation (precision/recall on anomalous test records)
  - Honest limitation notes

CRITICAL: Test data is never used for training or preprocessing fitting.
"""

from __future__ import annotations

import sys
from collections import Counter

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)

from app.ml import model_registry
from app.ml.exception_classifier import EXCEPTION_CLASSES


def evaluate() -> None:
    print("\n📊 LedgerPilot — Phase 3A ML Evaluation\n")
    print("─" * 60)

    # ── Load artifacts ────────────────────────────────────────────────────────
    print("→ Loading model artifacts and dataset splits...")
    try:
        classifier = model_registry.load_classifier()
        detector = model_registry.load_anomaly_detector()
        splits = model_registry.load_dataset_splits()
        metadata = model_registry.load_metadata()
    except FileNotFoundError as exc:
        print(f"\n❌ {exc}\n", file=sys.stderr)
        raise SystemExit(1)

    if splits is None:
        print("❌ No dataset splits found. Run training first.", file=sys.stderr)
        raise SystemExit(1)

    X_test = splits["X_test"].values
    y_test = splits["y_test"]
    X_train = splits["X_train"].values
    y_train = splits["y_train"]

    print(f"  Test samples : {len(y_test)}")
    print(f"  Train samples: {len(y_train)}")
    print(f"  Trained at   : {metadata.get('trained_at', 'unknown')}")

    # ── Exception Classifier evaluation ───────────────────────────────────────
    print("\n" + "═" * 60)
    print("  EXCEPTION CLASSIFIER (XGBoost)")
    print("═" * 60)

    preds = classifier.predict(X_test)
    y_pred = [p["predicted_type"] for p in preds]

    acc = accuracy_score(y_test, y_pred)
    macro_p = precision_score(y_test, y_pred, average="macro", zero_division=0)
    macro_r = recall_score(y_test, y_pred, average="macro", zero_division=0)
    macro_f1 = f1_score(y_test, y_pred, average="macro", zero_division=0)

    print(f"\n  Accuracy         : {acc:.4f}  ({acc*100:.1f}%)")
    print(f"  Macro Precision  : {macro_p:.4f}")
    print(f"  Macro Recall     : {macro_r:.4f}")
    print(f"  Macro F1         : {macro_f1:.4f}")

    print("\n  Per-class report:")
    report = classification_report(
        y_test, y_pred, zero_division=0, digits=3
    )
    for line in report.split("\n"):
        print("  " + line)

    # Confusion matrix (compact)
    labels = sorted(set(y_test))
    cm = confusion_matrix(y_test, y_pred, labels=labels)
    print("\n  Confusion matrix (rows=true, cols=predicted):")
    header = "  " + "  ".join(f"{l[:6]:>6s}" for l in labels)
    print(header)
    for i, row in enumerate(cm):
        row_str = "  ".join(f"{v:6d}" for v in row)
        print(f"  {labels[i][:6]:>6s}  {row_str}")

    # Sparse class warning
    test_dist = Counter(y_test)
    sparse_classes = [c for c, n in test_dist.items() if n < 10]
    if sparse_classes:
        print(
            f"\n  ⚠ WARNING: Classes with <10 test samples (metrics unreliable): "
            f"{sparse_classes}"
        )

    # ── Anomaly Detector evaluation ───────────────────────────────────────────
    print("\n" + "═" * 60)
    print("  ANOMALY DETECTOR (IsolationForest)")
    print("═" * 60)

    # Ground truth: NORMAL → not anomalous; everything else → anomalous
    y_anomaly_true = [label != "NORMAL" for label in y_test]
    anomaly_result = detector.predict(X_test)
    y_anomaly_pred = anomaly_result["is_anomaly"]

    tp = sum(t and p for t, p in zip(y_anomaly_true, y_anomaly_pred))
    fp = sum(not t and p for t, p in zip(y_anomaly_true, y_anomaly_pred))
    fn = sum(t and not p for t, p in zip(y_anomaly_true, y_anomaly_pred))
    tn = sum(not t and not p for t, p in zip(y_anomaly_true, y_anomaly_pred))

    prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0

    print(f"\n  True anomalies in test  : {sum(y_anomaly_true)}")
    print(f"  Predicted anomalies     : {sum(y_anomaly_pred)}")
    print(f"  True Positives          : {tp}")
    print(f"  False Positives         : {fp}")
    print(f"  False Negatives         : {fn}")
    print(f"  Precision               : {prec:.4f}")
    print(f"  Recall                  : {rec:.4f}")
    print(f"  F1                      : {f1:.4f}")
    print(f"  False Positive Rate     : {fpr:.4f}")
    print(
        "\n  NOTE: Anomaly detection is unsupervised (IsolationForest). "
        "These metrics\n"
        "  use synthetic ground truth and may not reflect real-world performance."
    )

    # ── Limitations ───────────────────────────────────────────────────────────
    print("\n" + "─" * 60)
    print("  KNOWN LIMITATIONS")
    print("─" * 60)
    print(
        "\n  1. Models trained on synthetic data only. Real-world performance"
        "\n     will differ and must be validated on real labeled data."
        "\n  2. Class imbalance may reduce recall for rare classes (UNKNOWN, DATE_MISMATCH)."
        "\n  3. Anomaly score normalisation (sigmoid) is a heuristic — not a probability."
        "\n  4. No cross-validation was performed due to dataset size."
        "\n"
    )

    print("✅ Evaluation complete.\n")


if __name__ == "__main__":
    try:
        evaluate()
    except Exception as exc:
        print(f"\n❌ Evaluation failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
