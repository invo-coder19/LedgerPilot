"""Model registry — versioned artifact persistence.

All model save/load operations go through here.
Never hardcode model filenames anywhere else.

Artifact layout:
  models/
    exception_classifier_v1.joblib
    anomaly_detector_v1.joblib
    metadata.json          — training metadata for both models
    dataset_splits.joblib  — saved train/val/test split indices

The registry is NOT a database — it is a local filesystem store for
model artifacts.  In production this would be replaced by MLflow,
a model registry, or cloud storage.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib

from app.core.config import get_settings

# ── File name helpers ──────────────────────────────────────────────────────────

CLASSIFIER_FILENAME = "exception_classifier_v1.joblib"
ANOMALY_FILENAME = "anomaly_detector_v1.joblib"
METADATA_FILENAME = "metadata.json"
DATASET_SPLITS_FILENAME = "dataset_splits.joblib"


def _models_dir() -> Path:
    return get_settings().models_path


# ── Save ──────────────────────────────────────────────────────────────────────

def save_classifier(model: Any) -> Path:
    """Save the exception classifier artifact."""
    path = _models_dir() / CLASSIFIER_FILENAME
    joblib.dump(model, path)
    print(f"  [registry] Saved classifier → {path}")
    return path


def save_anomaly_detector(model: Any) -> Path:
    """Save the anomaly detector artifact."""
    path = _models_dir() / ANOMALY_FILENAME
    joblib.dump(model, path)
    print(f"  [registry] Saved anomaly detector → {path}")
    return path


def save_metadata(metadata: dict[str, Any]) -> Path:
    """Persist training metadata as JSON."""
    path = _models_dir() / METADATA_FILENAME
    metadata["saved_at"] = datetime.now(timezone.utc).isoformat()
    with open(path, "w") as fh:
        json.dump(metadata, fh, indent=2, default=str)
    print(f"  [registry] Saved metadata → {path}")
    return path


def save_dataset_splits(splits: Any) -> Path:
    """Save train/val/test split indices for reproducible evaluation."""
    path = _models_dir() / DATASET_SPLITS_FILENAME
    joblib.dump(splits, path)
    print(f"  [registry] Saved dataset splits → {path}")
    return path


# ── Load ──────────────────────────────────────────────────────────────────────

def load_classifier() -> Any:
    """Load the exception classifier. Raises FileNotFoundError if missing."""
    path = _models_dir() / CLASSIFIER_FILENAME
    if not path.exists():
        raise FileNotFoundError(
            f"Classifier artifact not found at {path}. "
            "Run `python -m app.ml.training` first."
        )
    return joblib.load(path)


def load_anomaly_detector() -> Any:
    """Load the anomaly detector. Raises FileNotFoundError if missing."""
    path = _models_dir() / ANOMALY_FILENAME
    if not path.exists():
        raise FileNotFoundError(
            f"Anomaly detector artifact not found at {path}. "
            "Run `python -m app.ml.training` first."
        )
    return joblib.load(path)


def load_metadata() -> dict[str, Any]:
    """Load training metadata. Returns empty dict if not found."""
    path = _models_dir() / METADATA_FILENAME
    if not path.exists():
        return {}
    with open(path) as fh:
        return json.load(fh)


def load_dataset_splits() -> Any | None:
    """Load dataset splits. Returns None if not found."""
    path = _models_dir() / DATASET_SPLITS_FILENAME
    if not path.exists():
        return None
    return joblib.load(path)


def models_exist() -> bool:
    """Return True if both trained model artifacts exist."""
    d = _models_dir()
    return (d / CLASSIFIER_FILENAME).exists() and (d / ANOMALY_FILENAME).exists()
