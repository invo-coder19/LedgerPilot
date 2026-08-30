"""Evaluation metrics computation.

Calculates all required metrics from evaluation results:
  - Reconciliation: accuracy, precision, recall, FPR, FNR, unmatched rate
  - ML: per-class precision/recall/F1, macro/weighted F1, confusion matrix
  - AI Investigator: root-cause accuracy, citation correctness, uncertainty accuracy
  - Controller: decision accuracy, auto-resolution precision
  - Financial: false-positive cost, false-negative cost, autonomous error rate
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class ReconciliationMetrics:
    exact_match_accuracy: float = 0.0
    match_rate: float = 0.0
    precision: float = 0.0
    recall: float = 0.0
    false_positive_rate: float = 0.0
    false_negative_rate: float = 0.0
    unmatched_rate: float = 0.0
    total_cases: int = 0
    matched: int = 0
    unmatched: int = 0
    false_positives: int = 0
    false_negatives: int = 0


@dataclass
class MLMetrics:
    accuracy: float = 0.0
    precision_macro: float = 0.0
    recall_macro: float = 0.0
    f1_macro: float = 0.0
    f1_weighted: float = 0.0
    per_class: dict[str, dict] = field(default_factory=dict)
    confusion_matrix: list[list[int]] = field(default_factory=list)
    classes: list[str] = field(default_factory=list)


@dataclass
class AIInvestigatorMetrics:
    root_cause_accuracy: float = 0.0
    citation_correctness: float = 0.0
    uncertainty_accuracy: float = 0.0
    human_review_accuracy: float = 0.0
    unsupported_claim_rate: float = 0.0
    total_evaluated: int = 0


@dataclass
class ControllerMetrics:
    decision_accuracy: float = 0.0
    auto_resolution_precision: float = 0.0
    human_review_precision: float = 0.0
    escalation_precision: float = 0.0
    blocking_precision: float = 0.0
    action_success_rate: float = 0.0
    auto_resolution_rate: float = 0.0
    human_review_rate: float = 0.0
    escalation_rate: float = 0.0
    blocking_rate: float = 0.0
    total_decisions: int = 0


@dataclass
class FinancialMetrics:
    false_positive_cost: float = 0.0      # ₹ incorrectly auto-resolved
    false_negative_cost: float = 0.0      # ₹ unnecessarily escalated
    autonomous_error_rate: float = 0.0    # incorrect_auto / total_auto
    financial_error_rate: float = 0.0     # ₹_incorrect_auto / ₹_total_auto
    amount_processed: float = 0.0
    amount_auto_resolved: float = 0.0
    amount_incorrectly_auto_resolved: float = 0.0
    amount_under_review: float = 0.0
    amount_escalated: float = 0.0
    human_interventions_avoided: int = 0


def compute_reconciliation_metrics(
    ground_truth: list[dict],
    predictions: list[dict],
) -> ReconciliationMetrics:
    """Compute reconciliation metrics from ground truth vs predictions.

    Args:
        ground_truth: list of {case_id, expected_match_status, ...}
        predictions: list of {case_id, actual_match_status, ...}
    """
    gt_map = {c["case_id"]: c for c in ground_truth}
    pred_map = {p["case_id"]: p for p in predictions}

    total = len(ground_truth)
    matched = 0
    unmatched = 0
    fp = 0  # Predicted MATCHED, actually UNMATCHED
    fn = 0  # Predicted UNMATCHED, actually MATCHED

    for case_id, gt in gt_map.items():
        pred = pred_map.get(case_id, {})
        expected = gt.get("expected_match_status", "UNMATCHED")
        actual = pred.get("actual_match_status", "UNMATCHED")

        if actual == "MATCHED":
            matched += 1
        else:
            unmatched += 1

        if expected == "MATCHED" and actual != "MATCHED":
            fn += 1  # false negative — missed a valid match
        elif expected != "MATCHED" and actual == "MATCHED":
            fp += 1  # false positive — incorrectly matched

    correct = sum(
        1 for cid, gt in gt_map.items()
        if pred_map.get(cid, {}).get("actual_match_status") == gt["expected_match_status"]
    )

    precision = matched / (matched + fp) if (matched + fp) > 0 else 1.0
    recall = (matched - fn) / matched if matched > 0 else 0.0
    fpr = fp / (unmatched + fp) if (unmatched + fp) > 0 else 0.0
    fnr = fn / max(total - unmatched, 1)

    return ReconciliationMetrics(
        exact_match_accuracy=correct / max(total, 1),
        match_rate=matched / max(total, 1),
        precision=precision,
        recall=recall,
        false_positive_rate=fpr,
        false_negative_rate=fnr,
        unmatched_rate=unmatched / max(total, 1),
        total_cases=total,
        matched=matched,
        unmatched=unmatched,
        false_positives=fp,
        false_negatives=fn,
    )


def compute_ml_metrics(
    y_true: list[str],
    y_pred: list[str],
    classes: Optional[list[str]] = None,
) -> MLMetrics:
    """Compute ML classification metrics."""
    if not y_true:
        return MLMetrics()

    unique_classes = classes or sorted(set(y_true) | set(y_pred))

    # Build confusion matrix
    class_idx = {c: i for i, c in enumerate(unique_classes)}
    n = len(unique_classes)
    cm = [[0] * n for _ in range(n)]
    for true, pred in zip(y_true, y_pred):
        if true in class_idx and pred in class_idx:
            cm[class_idx[true]][class_idx[pred]] += 1

    # Per-class metrics
    per_class: dict[str, dict] = {}
    f1_scores = []
    f1_weighted = []
    for cls in unique_classes:
        idx = class_idx[cls]
        tp = cm[idx][idx]
        fp = sum(cm[r][idx] for r in range(n) if r != idx)
        fn = sum(cm[idx][c] for c in range(n) if c != idx)
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
        support = sum(cm[idx])
        per_class[cls] = {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "support": support,
        }
        f1_scores.append(f1)
        f1_weighted.append(f1 * support)

    correct = sum(y_true[i] == y_pred[i] for i in range(len(y_true)))
    accuracy = correct / len(y_true)
    f1_macro = sum(f1_scores) / len(f1_scores) if f1_scores else 0.0
    total_support = sum(v["support"] for v in per_class.values())
    f1_w = sum(f1_weighted) / total_support if total_support > 0 else 0.0

    # Macro precision/recall
    prec_macro = sum(per_class[c]["precision"] for c in unique_classes) / len(unique_classes)
    rec_macro = sum(per_class[c]["recall"] for c in unique_classes) / len(unique_classes)

    return MLMetrics(
        accuracy=round(accuracy, 4),
        precision_macro=round(prec_macro, 4),
        recall_macro=round(rec_macro, 4),
        f1_macro=round(f1_macro, 4),
        f1_weighted=round(f1_w, 4),
        per_class=per_class,
        confusion_matrix=cm,
        classes=unique_classes,
    )


def compute_controller_metrics(
    ground_truth: list[dict],
    decisions: list[dict],
) -> ControllerMetrics:
    """Compute controller decision accuracy and precision metrics."""
    gt_map = {c["case_id"]: c for c in ground_truth if c.get("expected_exception_type")}
    dec_map = {d["case_id"]: d for d in decisions}

    total = len(dec_map)
    if total == 0:
        return ControllerMetrics()

    correct = 0
    auto_count = 0
    auto_correct = 0
    review_count = 0
    review_correct = 0
    escalated_count = 0
    blocked_count = 0

    ACTION_CLASS_TO_DECISION = {
        "AUTO_RESOLVE_ALLOWED": "AUTO_EXECUTE",
        "HUMAN_REVIEW": "RECOMMEND",
        "BLOCK": "BLOCK",
        "NO_ACTION": "NO_ACTION",
    }

    for case_id, dec in dec_map.items():
        gt = gt_map.get(case_id)
        actual_decision = dec.get("actual_decision", "RECOMMEND")

        if gt:
            expected_decision = ACTION_CLASS_TO_DECISION.get(
                gt["expected_action_class"], "RECOMMEND"
            )
            if actual_decision == expected_decision:
                correct += 1

        if actual_decision == "AUTO_EXECUTE":
            auto_count += 1
            # Correct if the GT said AUTO_RESOLVE_ALLOWED
            if gt and gt.get("expected_action_class") == "AUTO_RESOLVE_ALLOWED":
                auto_correct += 1
        elif actual_decision == "RECOMMEND":
            review_count += 1
            if gt and gt.get("expected_action_class") == "HUMAN_REVIEW":
                review_correct += 1
        elif actual_decision == "ESCALATE":
            escalated_count += 1
        elif actual_decision == "BLOCK":
            blocked_count += 1

    return ControllerMetrics(
        decision_accuracy=correct / max(len(gt_map), 1),
        auto_resolution_precision=auto_correct / max(auto_count, 1),
        human_review_precision=review_correct / max(review_count, 1),
        auto_resolution_rate=auto_count / max(total, 1),
        human_review_rate=review_count / max(total, 1),
        escalation_rate=escalated_count / max(total, 1),
        blocking_rate=blocked_count / max(total, 1),
        total_decisions=total,
    )


def compute_financial_metrics(
    ground_truth: list[dict],
    decisions: list[dict],
) -> FinancialMetrics:
    """Compute financial cost of incorrect autonomous decisions."""
    dec_map = {d["case_id"]: d for d in decisions}
    gt_map = {c["case_id"]: c for c in ground_truth}

    amount_processed = 0.0
    amount_auto = 0.0
    amount_incorrect_auto = 0.0
    amount_review = 0.0
    amount_escalated = 0.0
    fp_cost = 0.0   # incorrectly auto-resolved (should have been reviewed)
    fn_cost = 0.0   # unnecessarily escalated (was safe to resolve)
    interventions_avoided = 0

    for case_id, dec in dec_map.items():
        gt = gt_map.get(case_id, {})
        amount = float(gt.get("amount", 0))
        actual_decision = dec.get("actual_decision", "RECOMMEND")
        expected_class = gt.get("expected_action_class", "HUMAN_REVIEW")

        amount_processed += amount

        if actual_decision == "AUTO_EXECUTE":
            amount_auto += amount
            if expected_class != "AUTO_RESOLVE_ALLOWED":
                # False positive — auto-resolved something that shouldn't be
                amount_incorrect_auto += amount
                fp_cost += amount
            else:
                interventions_avoided += 1
        elif actual_decision in ("RECOMMEND", "ESCALATE"):
            amount_review += amount
            if expected_class == "AUTO_RESOLVE_ALLOWED":
                # False negative — unnecessarily sent to review
                fn_cost += amount
        elif actual_decision == "BLOCK":
            amount_escalated += amount

    total_auto = len([d for d in decisions if d.get("actual_decision") == "AUTO_EXECUTE"])
    incorrect_auto = len([
        d for d in decisions
        if d.get("actual_decision") == "AUTO_EXECUTE"
        and gt_map.get(d["case_id"], {}).get("expected_action_class") != "AUTO_RESOLVE_ALLOWED"
    ])

    return FinancialMetrics(
        false_positive_cost=round(fp_cost, 2),
        false_negative_cost=round(fn_cost, 2),
        autonomous_error_rate=incorrect_auto / max(total_auto, 1),
        financial_error_rate=amount_incorrect_auto / max(amount_auto, 1) if amount_auto > 0 else 0.0,
        amount_processed=round(amount_processed, 2),
        amount_auto_resolved=round(amount_auto, 2),
        amount_incorrectly_auto_resolved=round(amount_incorrect_auto, 2),
        amount_under_review=round(amount_review, 2),
        amount_escalated=round(amount_escalated, 2),
        human_interventions_avoided=interventions_avoided,
    )


def all_metrics_to_dict(
    recon: ReconciliationMetrics,
    ml: MLMetrics,
    ai: AIInvestigatorMetrics,
    ctrl: ControllerMetrics,
    fin: FinancialMetrics,
) -> list[dict]:
    """Flatten all metrics to a list of {metric_name, metric_value, category} dicts."""
    rows = []

    def _add(category: str, name: str, value: float, metadata: Optional[dict] = None):
        rows.append({
            "metric_name": name,
            "metric_value": round(float(value), 4),
            "category": category,
            "metric_metadata": metadata,
        })

    # Reconciliation
    _add("reconciliation", "exact_match_accuracy", recon.exact_match_accuracy)
    _add("reconciliation", "match_rate", recon.match_rate)
    _add("reconciliation", "precision", recon.precision)
    _add("reconciliation", "recall", recon.recall)
    _add("reconciliation", "false_positive_rate", recon.false_positive_rate)
    _add("reconciliation", "false_negative_rate", recon.false_negative_rate)
    _add("reconciliation", "unmatched_rate", recon.unmatched_rate)

    # ML
    _add("ml", "accuracy", ml.accuracy)
    _add("ml", "f1_macro", ml.f1_macro)
    _add("ml", "f1_weighted", ml.f1_weighted)
    _add("ml", "precision_macro", ml.precision_macro)
    _add("ml", "recall_macro", ml.recall_macro)
    _add("ml", "confusion_matrix", 0.0, {"matrix": ml.confusion_matrix, "classes": ml.classes})
    for cls, m in ml.per_class.items():
        _add("ml", f"f1_{cls}", m["f1"], {"class": cls, **m})

    # AI Investigator
    _add("ai", "root_cause_accuracy", ai.root_cause_accuracy)
    _add("ai", "citation_correctness", ai.citation_correctness)
    _add("ai", "uncertainty_accuracy", ai.uncertainty_accuracy)
    _add("ai", "human_review_accuracy", ai.human_review_accuracy)
    _add("ai", "unsupported_claim_rate", ai.unsupported_claim_rate)

    # Controller
    _add("controller", "decision_accuracy", ctrl.decision_accuracy)
    _add("controller", "auto_resolution_precision", ctrl.auto_resolution_precision)
    _add("controller", "human_review_precision", ctrl.human_review_precision)
    _add("controller", "auto_resolution_rate", ctrl.auto_resolution_rate)
    _add("controller", "human_review_rate", ctrl.human_review_rate)
    _add("controller", "escalation_rate", ctrl.escalation_rate)
    _add("controller", "blocking_rate", ctrl.blocking_rate)

    # Financial
    _add("financial", "false_positive_cost_inr", fin.false_positive_cost)
    _add("financial", "false_negative_cost_inr", fin.false_negative_cost)
    _add("financial", "autonomous_error_rate", fin.autonomous_error_rate)
    _add("financial", "financial_error_rate", fin.financial_error_rate)
    _add("financial", "amount_processed_inr", fin.amount_processed)
    _add("financial", "amount_auto_resolved_inr", fin.amount_auto_resolved)
    _add("financial", "amount_incorrectly_auto_resolved_inr", fin.amount_incorrectly_auto_resolved)
    _add("financial", "human_interventions_avoided", fin.human_interventions_avoided)

    return rows
