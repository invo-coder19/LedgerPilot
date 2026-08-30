"""Evaluation CLI.

Usage:
  python -m app.evaluation generate_dataset --records 1000 --seed 42 --name benchmark_v1
  python -m app.evaluation run --dataset benchmark_v1
  python -m app.evaluation report --run <RUN_ID>
  python -m app.evaluation report --run <RUN_ID> --format markdown
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import datetime, timezone


def cmd_generate_dataset(args):
    """Generate and store a benchmark dataset."""
    from app.core.database import SessionLocal
    from app.evaluation.dataset_generator import BenchmarkDatasetGenerator
    from app.models.evaluation import EvaluationDataset

    print(f"Generating {args.records} records with seed={args.seed} ...")

    gen = BenchmarkDatasetGenerator(
        records=args.records,
        seed=args.seed,
        dataset_name=args.name,
        version=args.version,
    )
    data = gen.generate()

    db = SessionLocal()
    try:
        # Check if version already exists
        existing = (
            db.query(EvaluationDataset)
            .filter(
                EvaluationDataset.name == args.name,
                EvaluationDataset.version == args.version,
            )
            .first()
        )
        if existing:
            print(f"Dataset '{args.name}' v{args.version} already exists (id={existing.id})")
            print("Use --version to specify a different version.")
            return

        dataset = EvaluationDataset(
            name=args.name,
            version=args.version,
            description=f"Benchmark dataset: {args.records} cases, seed={args.seed}",
            record_count=args.records,
            random_seed=args.seed,
            distribution=data["metadata"]["distribution_config"],
            split_config={"benchmark": 1.0},
            cases=data["cases"],
            metadata_={
                "generated_at": data["metadata"]["generated_at"],
                "scenario_counts": data["metadata"]["scenario_counts"],
                "actual_distribution": data["metadata"]["actual_distribution"],
            },
            is_active=True,
        )
        db.add(dataset)
        db.commit()
        db.refresh(dataset)

        print(f"\n✓ Dataset stored: {dataset.id}")
        print(f"  Name: {args.name} v{args.version}")
        print(f"  Records: {args.records}")
        print(f"  Seed: {args.seed}")
        print("\nScenario distribution:")
        for scenario, count in data["metadata"]["scenario_counts"].items():
            pct = count / args.records * 100
            print(f"  {scenario:25s}: {count:5d} ({pct:.1f}%)")

        # Also save synthetic records to a JSON file for reference
        if args.output:
            with open(args.output, "w") as f:
                json.dump(data, f, indent=2, default=str)
            print(f"\n✓ Full dataset written to: {args.output}")

    finally:
        db.close()


def cmd_run_evaluation(args):
    """Run an evaluation against a stored dataset."""
    from app.core.database import SessionLocal
    from app.evaluation.evaluator import run_evaluation
    from app.core.config import get_settings
    import subprocess

    settings = get_settings()

    # Build configuration metadata for reproducibility
    try:
        git_commit = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], stderr=subprocess.DEVNULL
        ).decode().strip()
    except Exception:
        git_commit = "unknown"

    configuration = {
        "app_version": settings.APP_VERSION,
        "git_commit": git_commit,
        "llm_provider": settings.LLM_PROVIDER,
        "embedding_model": settings.EMBEDDING_MODEL,
        "evaluation_timestamp": datetime.now(timezone.utc).isoformat(),
        "dataset": args.dataset,
    }

    print(f"Running evaluation against dataset '{args.dataset}' ...")
    print(f"  App version: {settings.APP_VERSION}")
    print(f"  Git commit: {git_commit}")

    db = SessionLocal()
    try:
        run = run_evaluation(
            db=db,
            dataset_name=args.dataset,
            version=args.version,
            configuration=configuration,
        )
        print(f"\n✓ Evaluation completed: {run.id}")
        print(f"  Status: {run.status.value}")
        print(f"  Records: {run.records_tested}")
        print(f"  Duration: {run.duration_seconds:.1f}s")
        print(f"\nUse: python -m app.evaluation report --run {run.id}")
    finally:
        db.close()


def cmd_report(args):
    """Generate a report for an evaluation run."""
    from app.core.database import SessionLocal
    from app.evaluation.report import generate_json_report, generate_markdown_report

    db = SessionLocal()
    try:
        run_id = uuid.UUID(args.run)

        if args.format == "markdown":
            report = generate_markdown_report(db, run_id)
            print(report)
            if args.output:
                with open(args.output, "w", encoding="utf-8") as f:
                    f.write(report)
                print(f"\n✓ Markdown report written to: {args.output}")
        else:
            report = generate_json_report(db, run_id)
            output = json.dumps(report, indent=2, default=str)
            print(output)
            if args.output:
                with open(args.output, "w", encoding="utf-8") as f:
                    f.write(output)
                print(f"\n✓ JSON report written to: {args.output}", file=sys.stderr)
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(
        prog="python -m app.evaluation",
        description="LedgerPilot Evaluation CLI",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # generate_dataset
    gen_parser = subparsers.add_parser("generate_dataset", help="Generate benchmark dataset")
    gen_parser.add_argument("--records", type=int, default=1000, help="Number of cases (default: 1000)")
    gen_parser.add_argument("--seed", type=int, default=42, help="Random seed (default: 42)")
    gen_parser.add_argument("--name", type=str, default="benchmark_v1", help="Dataset name")
    gen_parser.add_argument("--version", type=str, default="v1", help="Dataset version")
    gen_parser.add_argument("--output", type=str, default=None, help="Optional output JSON file")

    # run
    run_parser = subparsers.add_parser("run", help="Run an evaluation")
    run_parser.add_argument("--dataset", type=str, required=True, help="Dataset name")
    run_parser.add_argument("--version", type=str, default="v1", help="Run version tag")

    # report
    rep_parser = subparsers.add_parser("report", help="Generate evaluation report")
    rep_parser.add_argument("--run", type=str, required=True, help="Evaluation run ID (UUID)")
    rep_parser.add_argument("--format", choices=["json", "markdown"], default="json")
    rep_parser.add_argument("--output", type=str, default=None, help="Output file path")

    args = parser.parse_args()

    if args.command == "generate_dataset":
        cmd_generate_dataset(args)
    elif args.command == "run":
        cmd_run_evaluation(args)
    elif args.command == "report":
        cmd_report(args)


if __name__ == "__main__":
    main()
