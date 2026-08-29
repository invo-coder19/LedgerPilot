"""ML package for LedgerPilot — Phase 3A Intelligence Foundation.

Components:
  features.py          — Feature engineering from financial ORM records
  anomaly_detection.py — IsolationForest anomaly detector
  exception_classifier.py — XGBoost multi-class classifier
  model_registry.py    — Versioned model artifact loader/saver
  dataset.py           — Synthetic labeled dataset generator
  training.py          — Training pipeline (python -m app.ml.training)
  evaluation.py        — Evaluation report (python -m app.ml.evaluation)
  inference.py         — Inference service (called from API routes)
"""
