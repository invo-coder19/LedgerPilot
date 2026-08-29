"""Phase 3B — AI Investigation tables.

Revision: 003
Creates:
  - ai_investigation_runs
  - ai_investigation_steps
  - Extends auditaction enum with Phase 3B values
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None

# Phase 3B audit action values to add
NEW_AUDIT_ACTIONS = [
    "AI_INVESTIGATION_STARTED",
    "AI_EVIDENCE_RETRIEVED",
    "AI_INVESTIGATION_COMPLETED",
    "AI_INVESTIGATION_FAILED",
    "COPILOT_QUERY",
]


def upgrade() -> None:
    conn = op.get_bind()

    # ── 1. Extend auditaction enum ────────────────────────────────────────────
    for action in NEW_AUDIT_ACTIONS:
        conn.execute(
            sa.text(f"ALTER TYPE auditaction ADD VALUE IF NOT EXISTS '{action}'")
        )

    # ── 2. Create investigationstatus enum ────────────────────────────────────
    investigation_status_enum = postgresql.ENUM(
        "PENDING", "RUNNING", "COMPLETED", "FAILED",
        name="investigationstatus",
        create_type=False,
    )
    investigation_status_enum.create(conn, checkfirst=True)

    # ── 3. ai_investigation_runs ──────────────────────────────────────────────
    op.create_table(
        "ai_investigation_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "exception_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("exceptions.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "merchant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("merchants.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "status",
            sa.Enum("PENDING", "RUNNING", "COMPLETED", "FAILED", name="investigationstatus"),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("model_provider", sa.String(32), nullable=True),
        sa.Column("model_name", sa.String(128), nullable=True),
        sa.Column("model_version", sa.String(64), nullable=True),
        sa.Column("final_result", postgresql.JSONB(), nullable=True),
        sa.Column("final_confidence", sa.Float(), nullable=True),
        sa.Column("confidence_band", sa.String(16), nullable=True),
        sa.Column("requires_human", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
    )

    # ── 4. ai_investigation_steps ─────────────────────────────────────────────
    op.create_table(
        "ai_investigation_steps",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "investigation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ai_investigation_runs.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("step_name", sa.String(128), nullable=False),
        sa.Column("tool_name", sa.String(128), nullable=True),
        sa.Column("input_summary", sa.Text(), nullable=True),
        sa.Column("output_summary", sa.Text(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )


def downgrade() -> None:
    op.drop_table("ai_investigation_steps")
    op.drop_table("ai_investigation_runs")
    # Note: Postgres enum values cannot be removed easily — leave enum intact
