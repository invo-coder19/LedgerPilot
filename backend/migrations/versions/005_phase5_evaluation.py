"""Phase 5 — Evaluation tables.

Creates:
  evaluation_datasets  — versioned benchmark ground-truth datasets
  evaluation_runs      — individual evaluation executions
  evaluation_results   — metric name/value rows (queryable per run)
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "005_phase5_evaluation"
down_revision = "004_phase4_controller"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── evaluation_datasets ───────────────────────────────────────────────────
    op.create_table(
        "evaluation_datasets",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("version", sa.String(32), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("record_count", sa.Integer, default=0, nullable=False),
        sa.Column("random_seed", sa.Integer, nullable=True),
        sa.Column("distribution", sa.JSON, nullable=True),
        sa.Column("split_config", sa.JSON, nullable=True),
        sa.Column("cases", sa.JSON, nullable=True),
        sa.Column("metadata", sa.JSON, nullable=True),
        sa.Column("is_active", sa.Boolean, default=True, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_unique_constraint(
        "uq_eval_dataset_name_version", "evaluation_datasets", ["name", "version"]
    )
    op.create_index("ix_eval_datasets_name", "evaluation_datasets", ["name"])

    # ── evaluation_runs ───────────────────────────────────────────────────────
    op.create_table(
        "evaluation_runs",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "dataset_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("evaluation_datasets.id"),
            nullable=False,
        ),
        sa.Column("version", sa.String(32), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "PENDING", "RUNNING", "COMPLETED", "FAILED",
                name="evaluation_status",
            ),
            default="PENDING",
            nullable=False,
        ),
        sa.Column("records_tested", sa.Integer, default=0, nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Float, nullable=True),
        sa.Column("configuration", sa.JSON, nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_eval_runs_dataset_id", "evaluation_runs", ["dataset_id"])
    op.create_index("ix_eval_runs_status", "evaluation_runs", ["status"])

    # ── evaluation_results ────────────────────────────────────────────────────
    op.create_table(
        "evaluation_results",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "evaluation_run_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("evaluation_runs.id"),
            nullable=False,
        ),
        sa.Column("metric_name", sa.String(128), nullable=False),
        sa.Column("metric_value", sa.Float, nullable=False),
        sa.Column("metric_metadata", sa.JSON, nullable=True),
        sa.Column("category", sa.String(64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_eval_results_run_id", "evaluation_results", ["evaluation_run_id"])
    op.create_unique_constraint(
        "uq_eval_result_run_metric",
        "evaluation_results",
        ["evaluation_run_id", "metric_name"],
    )


def downgrade() -> None:
    op.drop_table("evaluation_results")
    op.drop_table("evaluation_runs")
    op.drop_table("evaluation_datasets")
    op.execute("DROP TYPE IF EXISTS evaluation_status")
