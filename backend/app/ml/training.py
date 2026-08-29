"""Training pipeline for Phase 3A ML models.

Usage:
    python -m app.ml.training

Steps:
    1. Generate labeled synthetic dataset
    2. Split train/val/test (before ANY preprocessing)
    3. Fit and train ExceptionClassifier
    4. Fit and train AnomalyDetector
    5. Save model artifacts
    6. Save metadata + dataset splits
    7. Print summary
"""

from __future__ import annotations

import sys
from collections import Counter
from datetime import datetime, timezone

import numpy as np

from app.core.config import get_settings
from app.ml import model_registry
from app.ml.anomaly_detection import AnomalyDetector
from app.ml.dataset import generate_dataset, train_val_test_split
from app.ml.exception_classifier import EXCEPTION_CLASSES, ExceptionClassifier


def train() -> None:
    settings = get_settings()
    seed = settings.ML_RANDOM_SEED

    print("\n🤖 LedgerPilot — Phase 3A ML Training\n")
    print("─" * 50)

    # ── Step 1: Generate dataset ───────────────────────────────────────────────
    print("→ Generating synthetic dataset...")
    X_df, y = generate_dataset(seed=seed)
    total = len(y)
    print(f"  Total samples: {total}")
    dist = Counter(y)
    for cls, cnt in sorted(dist.items()):
        pct = cnt / total * 100
        print(f"    {cls:25s}: {cnt:4d}  ({pct:.1f}%)")

    # ── Step 2: Split (BEFORE any preprocessing) ───────────────────────────────
    print("\n→ Splitting dataset (train/val/test)...")
    X_train, X_val, X_test, y_train, y_val, y_test = train_val_test_split(
        X_df, y, seed=seed
    )
    print(f"  Train : {len(y_train)} samples")
    print(f"  Val   : {len(y_val)} samples")
    print(f"  Test  : {len(y_test)} samples")

    # ── Step 3: Train exception classifier ────────────────────────────────────
    print("\n→ Training ExceptionClassifier (XGBoost)...")
    classifier = ExceptionClassifier(random_seed=seed)
    classifier.fit(
        X_train.values, y_train,
        X_val=X_val.values, y_val=y_val,
    )
    print("  ExceptionClassifier trained ✓")

    # ── Step 4: Train anomaly detector ────────────────────────────────────────
    print("\n→ Training AnomalyDetector (IsolationForest)...")
    # Train only on NORMAL records to learn the "normal" distribution
    normal_mask = [label == "NORMAL" for label in y_train]
    X_normal = X_train.values[normal_mask]
    detector = AnomalyDetector(random_seed=seed)
    detector.fit(X_normal)
    print(f"  AnomalyDetector trained on {X_normal.shape[0]} normal samples ✓")

    # ── Step 5: Save artifacts ────────────────────────────────────────────────
    print("\n→ Saving model artifacts...")
    model_registry.save_classifier(classifier)
    model_registry.save_anomaly_detector(detector)

    # ── Step 6: Save metadata + splits ────────────────────────────────────────
    metadata = {
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "seed": seed,
        "total_samples": total,
        "train_samples": len(y_train),
        "val_samples": len(y_val),
        "test_samples": len(y_test),
        "class_distribution": dict(dist),
        "classifier_version": ExceptionClassifier.MODEL_VERSION,
        "anomaly_detector_version": AnomalyDetector.MODEL_VERSION,
        "exception_classes": EXCEPTION_CLASSES,
        "anomaly_contamination": AnomalyDetector.CONTAMINATION,
        "note": (
            "Models trained on synthetic data for demonstration. "
            "In production, use real labeled financial data."
        ),
    }
    model_registry.save_metadata(metadata)
    model_registry.save_dataset_splits({
        "X_train": X_train, "X_val": X_val, "X_test": X_test,
        "y_train": y_train, "y_val": y_val, "y_test": y_test,
    })

    print("\n✅ Training complete!")
    print(f"   Artifacts → {model_registry._models_dir()}")
    print("   Run `python -m app.ml.evaluation` for evaluation metrics.\n")


if __name__ == "__main__":
    try:
        train()
    except Exception as exc:
        print(f"\n❌ Training failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
