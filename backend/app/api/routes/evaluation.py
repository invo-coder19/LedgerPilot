"""Evaluation API routes."""

from __future__ import annotations

import math
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser, require_role
from app.core.database import get_db
from app.models.evaluation import EvaluationDataset, EvaluationResult, EvaluationRun, EvaluationStatus
from app.models.user import Role
from app.schemas.evaluation import (
    EvaluationCompareResponse,
    EvaluationDatasetResponse,
    EvaluationRunCreate,
    EvaluationRunDetailResponse,
    EvaluationRunResponse,
    EvaluationSummaryResponse,
    GenerateDatasetRequest,
)

router = APIRouter(prefix="/evaluation", tags=["Evaluation"])


@router.get("/datasets", response_model=list[EvaluationDatasetResponse])
def list_datasets(
    current_user: CurrentUser = require_role(Role.ADMIN, Role.FINANCE_MANAGER, Role.FINANCE_ANALYST),
    db: Session = Depends(get_db),
):
    """List all evaluation datasets."""
    datasets = db.query(EvaluationDataset).order_by(EvaluationDataset.created_at.desc()).all()
    return [EvaluationDatasetResponse.model_validate(d) for d in datasets]


@router.post("/datasets", response_model=EvaluationDatasetResponse, status_code=status.HTTP_201_CREATED)
def generate_dataset(
    body: GenerateDatasetRequest,
    current_user: CurrentUser = require_role(Role.ADMIN, Role.FINANCE_MANAGER),
    db: Session = Depends(get_db),
):
    """Generate and store a new benchmark dataset. FINANCE_MANAGER+ only."""
    from app.evaluation.dataset_generator import BenchmarkDatasetGenerator
    from app.models.evaluation import EvaluationDataset

    # Check uniqueness
    existing = db.query(EvaluationDataset).filter(
        EvaluationDataset.name == body.name,
        EvaluationDataset.version == body.version,
    ).first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Dataset '{body.name}' v{body.version} already exists.",
        )

    gen = BenchmarkDatasetGenerator(
        records=body.records,
        seed=body.seed,
        dataset_name=body.name,
        version=body.version,
        distribution=body.distribution,
    )
    data = gen.generate()

    dataset = EvaluationDataset(
        name=body.name,
        version=body.version,
        description=f"Benchmark: {body.records} cases, seed={body.seed}",
        record_count=body.records,
        random_seed=body.seed,
        distribution=data["metadata"]["distribution_config"],
        split_config={"benchmark": 1.0},
        cases=data["cases"],
        metadata_=data["metadata"],
        is_active=True,
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)
    return EvaluationDatasetResponse.model_validate(dataset)


@router.get("/runs", response_model=list[EvaluationRunResponse])
def list_runs(
    current_user: CurrentUser = require_role(Role.ADMIN, Role.FINANCE_MANAGER, Role.FINANCE_ANALYST),
    db: Session = Depends(get_db),
):
    """List all evaluation runs."""
    runs = db.query(EvaluationRun).order_by(EvaluationRun.created_at.desc()).all()
    return [EvaluationRunResponse.model_validate(r) for r in runs]


@router.post("/runs", response_model=EvaluationRunResponse, status_code=status.HTTP_201_CREATED)
def create_run(
    body: EvaluationRunCreate,
    background_tasks: BackgroundTasks,
    current_user: CurrentUser = require_role(Role.ADMIN, Role.FINANCE_MANAGER),
    db: Session = Depends(get_db),
):
    """Start an evaluation run against a dataset."""
    from app.evaluation.evaluator import run_evaluation

    try:
        run = run_evaluation(db=db, dataset_name=body.dataset_name, version=body.version)
        return EvaluationRunResponse.model_validate(run)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/runs/{run_id}", response_model=EvaluationRunDetailResponse)
def get_run(
    run_id: uuid.UUID,
    current_user: CurrentUser = require_role(Role.ADMIN, Role.FINANCE_MANAGER, Role.FINANCE_ANALYST),
    db: Session = Depends(get_db),
):
    """Get evaluation run with all metrics."""
    run = db.get(EvaluationRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Evaluation run not found")

    results = db.query(EvaluationResult).filter(
        EvaluationResult.evaluation_run_id == run_id
    ).all()

    metrics = {
        r.metric_name: {"value": r.metric_value, "category": r.category, "metadata": r.metric_metadata}
        for r in results
    }

    return EvaluationRunDetailResponse(
        **EvaluationRunResponse.model_validate(run).model_dump(),
        metrics=metrics,
    )


@router.get("/runs/{run_id}/report")
def get_report(
    run_id: uuid.UUID,
    format: str = Query("json", regex="^(json|markdown)$"),
    current_user: CurrentUser = require_role(Role.ADMIN, Role.FINANCE_MANAGER, Role.FINANCE_ANALYST),
    db: Session = Depends(get_db),
):
    """Get evaluation report in JSON or Markdown."""
    from app.evaluation.report import generate_json_report, generate_markdown_report
    from fastapi.responses import PlainTextResponse

    run = db.get(EvaluationRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Evaluation run not found")

    if format == "markdown":
        return PlainTextResponse(generate_markdown_report(db, run_id))
    return generate_json_report(db, run_id)


@router.get("/summary", response_model=EvaluationSummaryResponse)
def get_summary(
    current_user: CurrentUser = require_role(Role.ADMIN, Role.FINANCE_MANAGER, Role.FINANCE_ANALYST),
    db: Session = Depends(get_db),
):
    """Get latest evaluation summary for the competition dashboard."""
    latest_run = (
        db.query(EvaluationRun)
        .filter(EvaluationRun.status == EvaluationStatus.COMPLETED)
        .order_by(EvaluationRun.completed_at.desc())
        .first()
    )

    if not latest_run:
        return EvaluationSummaryResponse(status="NO_DATA")

    results = db.query(EvaluationResult).filter(
        EvaluationResult.evaluation_run_id == latest_run.id
    ).all()

    m = {r.metric_name: r.metric_value for r in results}

    return EvaluationSummaryResponse(
        run_id=str(latest_run.id),
        records_tested=latest_run.records_tested,
        dataset_version=latest_run.version,
        status=latest_run.status.value,
        reconciliation_accuracy=m.get("exact_match_accuracy", 0.0),
        match_rate=m.get("match_rate", 0.0),
        reconciliation_precision=m.get("precision", 0.0),
        reconciliation_recall=m.get("recall", 0.0),
        false_positive_rate=m.get("false_positive_rate", 0.0),
        ml_accuracy=m.get("accuracy", 0.0),
        ml_f1_macro=m.get("f1_macro", 0.0),
        ml_f1_weighted=m.get("f1_weighted", 0.0),
        citation_correctness=m.get("citation_correctness", 0.0),
        uncertainty_accuracy=m.get("uncertainty_accuracy", 0.0),
        auto_resolution_precision=m.get("auto_resolution_precision", 0.0),
        auto_resolution_rate=m.get("auto_resolution_rate", 0.0),
        human_review_rate=m.get("human_review_rate", 0.0),
        escalation_rate=m.get("escalation_rate", 0.0),
        decision_accuracy=m.get("decision_accuracy", 0.0),
        false_positive_cost_inr=m.get("false_positive_cost_inr", 0.0),
        false_negative_cost_inr=m.get("false_negative_cost_inr", 0.0),
        autonomous_error_rate=m.get("autonomous_error_rate", 0.0),
        financial_error_rate=m.get("financial_error_rate", 0.0),
        amount_processed_inr=m.get("amount_processed_inr", 0.0),
        amount_auto_resolved_inr=m.get("amount_auto_resolved_inr", 0.0),
        human_interventions_avoided=int(m.get("human_interventions_avoided", 0)),
    )


@router.get("/compare", response_model=EvaluationCompareResponse)
def compare_runs(
    run_a: uuid.UUID = Query(...),
    run_b: uuid.UUID = Query(...),
    current_user: CurrentUser = require_role(Role.ADMIN, Role.FINANCE_MANAGER, Role.FINANCE_ANALYST),
    db: Session = Depends(get_db),
):
    """Compare two evaluation runs side-by-side."""
    def _get_run_detail(rid):
        run = db.get(EvaluationRun, rid)
        if not run:
            raise HTTPException(status_code=404, detail=f"Run {rid} not found")
        results = db.query(EvaluationResult).filter(
            EvaluationResult.evaluation_run_id == rid
        ).all()
        metrics = {r.metric_name: {"value": r.metric_value, "category": r.category} for r in results}
        return EvaluationRunDetailResponse(
            **EvaluationRunResponse.model_validate(run).model_dump(),
            metrics=metrics,
        )

    a = _get_run_detail(run_a)
    b = _get_run_detail(run_b)

    # Compute metric diffs
    diff = {}
    for metric_name in set(a.metrics) | set(b.metrics):
        val_a = a.metrics.get(metric_name, {}).get("value", None)
        val_b = b.metrics.get(metric_name, {}).get("value", None)
        if val_a is not None and val_b is not None:
            diff[metric_name] = {
                "run_a": val_a,
                "run_b": val_b,
                "delta": round(val_b - val_a, 4),
                "improved": val_b > val_a,
            }

    return EvaluationCompareResponse(run_a=a, run_b=b, diff=diff)
