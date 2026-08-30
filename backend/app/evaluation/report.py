"""Evaluation report generator — produces JSON and Markdown reports."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models.evaluation import EvaluationResult, EvaluationRun


def get_run_metrics(db: Session, run_id) -> dict[str, Any]:
    """Load all metrics for a run as a structured dict."""
    run = db.get(EvaluationRun, run_id)
    if not run:
        raise ValueError(f"Evaluation run {run_id} not found")

    results = db.query(EvaluationResult).filter(
        EvaluationResult.evaluation_run_id == run_id
    ).all()

    metrics: dict[str, dict] = {}
    for r in results:
        metrics[r.metric_name] = {
            "value": r.metric_value,
            "category": r.category,
            "metadata": r.metric_metadata,
        }

    return {
        "run_id": str(run.id),
        "dataset_id": str(run.dataset_id),
        "version": run.version,
        "status": run.status.value,
        "records_tested": run.records_tested,
        "duration_seconds": run.duration_seconds,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "configuration": run.configuration or {},
        "metrics": metrics,
    }


def generate_json_report(db: Session, run_id) -> dict:
    """Generate machine-readable benchmark report."""
    from app.core.config import get_settings
    settings = get_settings()

    data = get_run_metrics(db, run_id)
    m = data["metrics"]

    def _v(name: str, default: float = 0.0) -> float:
        return m.get(name, {}).get("value", default)

    report = {
        "report_type": "benchmark_report",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "disclaimer": (
            "SYNTHETIC BENCHMARK — All data is synthetically generated. "
            "No real merchant data. No real money movement. "
            "Results do not represent Razorpay production performance."
        ),
        "evaluation_run": {
            "run_id": data["run_id"],
            "dataset_version": data["version"],
            "records_tested": data["records_tested"],
            "duration_seconds": data["duration_seconds"],
            "configuration": data["configuration"],
        },
        "reconciliation": {
            "exact_match_accuracy": _v("exact_match_accuracy"),
            "match_rate": _v("match_rate"),
            "precision": _v("precision"),
            "recall": _v("recall"),
            "false_positive_rate": _v("false_positive_rate"),
            "false_negative_rate": _v("false_negative_rate"),
            "unmatched_rate": _v("unmatched_rate"),
        },
        "ml_classification": {
            "accuracy": _v("accuracy"),
            "f1_macro": _v("f1_macro"),
            "f1_weighted": _v("f1_weighted"),
            "precision_macro": _v("precision_macro"),
            "recall_macro": _v("recall_macro"),
        },
        "ai_investigator": {
            "citation_correctness": _v("citation_correctness"),
            "uncertainty_accuracy": _v("uncertainty_accuracy"),
            "human_review_accuracy": _v("human_review_accuracy"),
            "unsupported_claim_rate": _v("unsupported_claim_rate"),
        },
        "controller": {
            "decision_accuracy": _v("decision_accuracy"),
            "auto_resolution_precision": _v("auto_resolution_precision"),
            "auto_resolution_rate": _v("auto_resolution_rate"),
            "human_review_rate": _v("human_review_rate"),
            "escalation_rate": _v("escalation_rate"),
            "blocking_rate": _v("blocking_rate"),
        },
        "financial": {
            "amount_processed_inr": _v("amount_processed_inr"),
            "amount_auto_resolved_inr": _v("amount_auto_resolved_inr"),
            "amount_incorrectly_auto_resolved_inr": _v("amount_incorrectly_auto_resolved_inr"),
            "false_positive_cost_inr": _v("false_positive_cost_inr"),
            "false_negative_cost_inr": _v("false_negative_cost_inr"),
            "autonomous_error_rate": _v("autonomous_error_rate"),
            "financial_error_rate": _v("financial_error_rate"),
            "human_interventions_avoided": int(_v("human_interventions_avoided")),
        },
    }
    return report


def generate_markdown_report(db: Session, run_id) -> str:
    """Generate human-readable Markdown benchmark report."""
    report = generate_json_report(db, run_id)

    def pct(v: float) -> str:
        return f"{v * 100:.1f}%"

    def inr(v: float) -> str:
        if v >= 10_00_000:
            return f"₹{v / 10_00_000:.2f}L"
        if v >= 1000:
            return f"₹{v:,.0f}"
        return f"₹{v:.2f}"

    r = report["reconciliation"]
    ml = report["ml_classification"]
    ai = report["ai_investigator"]
    ctrl = report["controller"]
    fin = report["financial"]
    ev = report["evaluation_run"]

    lines = [
        "# LedgerPilot — Benchmark Report",
        "",
        f"> {report['disclaimer']}",
        "",
        "## Evaluation Details",
        f"- **Run ID:** `{ev['run_id']}`",
        f"- **Records Tested:** {ev['records_tested']:,}",
        f"- **Duration:** {ev['duration_seconds']:.1f}s",
        f"- **Generated:** {report['generated_at']}",
        "",
        "## Reconciliation",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Exact Match Accuracy | **{pct(r['exact_match_accuracy'])}** |",
        f"| Match Rate | {pct(r['match_rate'])} |",
        f"| Precision | {pct(r['precision'])} |",
        f"| Recall | {pct(r['recall'])} |",
        f"| False Positive Rate | {pct(r['false_positive_rate'])} |",
        f"| False Negative Rate | {pct(r['false_negative_rate'])} |",
        "",
        "## ML Exception Classification",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Accuracy | **{pct(ml['accuracy'])}** |",
        f"| F1 Macro | {pct(ml['f1_macro'])} |",
        f"| F1 Weighted | {pct(ml['f1_weighted'])} |",
        "",
        "## AI Investigator",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Citation Correctness | **{pct(ai['citation_correctness'])}** |",
        f"| Uncertainty Accuracy | {pct(ai['uncertainty_accuracy'])} |",
        f"| Human Review Accuracy | {pct(ai['human_review_accuracy'])} |",
        "",
        "## Controller Decisions",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Decision Accuracy | **{pct(ctrl['decision_accuracy'])}** |",
        f"| Auto-Resolution Precision | **{pct(ctrl['auto_resolution_precision'])}** |",
        f"| Auto-Resolution Rate | {pct(ctrl['auto_resolution_rate'])} |",
        f"| Human Review Rate | {pct(ctrl['human_review_rate'])} |",
        f"| Escalation Rate | {pct(ctrl['escalation_rate'])} |",
        "",
        "## Financial Impact",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Amount Processed | **{inr(fin['amount_processed_inr'])}** |",
        f"| Amount Auto-Resolved | {inr(fin['amount_auto_resolved_inr'])} |",
        f"| False-Positive Cost (Incorrectly Auto-Resolved) | {inr(fin['false_positive_cost_inr'])} |",
        f"| False-Negative Cost (Unnecessarily Escalated) | {inr(fin['false_negative_cost_inr'])} |",
        f"| Autonomous Action Error Rate | {pct(fin['autonomous_error_rate'])} |",
        f"| Financial Auto-Resolution Error Rate | {pct(fin['financial_error_rate'])} |",
        f"| Human Interventions Avoided | {int(fin['human_interventions_avoided']):,} |",
        "",
        "## Trust Properties",
        "✓ Evidence-backed AI decisions",
        "✓ Confidence-gated actions",
        "✓ Deterministic policy engine",
        "✓ Human approval for risky cases",
        "✓ No unrestricted LLM actions",
        "✓ Complete audit trail",
        "✓ Kill switch implemented",
        "✓ Failure detection and safe fallback",
        "✓ Reproducible benchmark (seeded synthetic data)",
        "",
        "---",
        "_All results are on synthetic benchmark data. No real financial data used._",
    ]
    return "\n".join(lines)
