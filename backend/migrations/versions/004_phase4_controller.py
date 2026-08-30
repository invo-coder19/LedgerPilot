"""Phase 4 — Autonomous Controller tables.

Revision ID: 004_phase4_ctrl
Revises: 003_phase3b_investigations
Create Date: 2026-08-30
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

# revision identifiers
revision = "004_phase4_ctrl"
down_revision = "003_phase3b_investigations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── controller_runs ───────────────────────────────────────────────────────
    op.create_table(
        "controller_runs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("merchant_id", UUID(as_uuid=True), sa.ForeignKey("merchants.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("reconciliation_run_id", sa.String(128), nullable=True, index=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="QUEUED", index=True),
        sa.Column("dry_run", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("total_exceptions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("processed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("auto_executed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("recommended", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("escalated", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("blocked", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("amount_processed", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("amount_auto_resolved", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("amount_awaiting_review", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("amount_escalated", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("error_message", sa.Text(), nullable=True),
    )

    # ── controller_decisions ──────────────────────────────────────────────────
    op.create_table(
        "controller_decisions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("controller_run_id", UUID(as_uuid=True), sa.ForeignKey("controller_runs.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("exception_id", UUID(as_uuid=True), sa.ForeignKey("exceptions.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("investigation_id", UUID(as_uuid=True), sa.ForeignKey("ai_investigation_runs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("decision", sa.String(32), nullable=False, index=True),
        sa.Column("action", sa.String(128), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0"),
        sa.Column("risk_score", sa.Float(), nullable=False, server_default="1"),
        sa.Column("risk_band", sa.String(16), nullable=False, server_default="CRITICAL"),
        sa.Column("reason", sa.Text(), nullable=False, server_default=""),
        sa.Column("evidence_ids", JSONB, nullable=True),
        sa.Column("policy_version", sa.String(64), nullable=True),
        sa.Column("requires_approval", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("status", sa.String(32), nullable=False, server_default="PENDING", index=True),
        sa.Column("risk_details", JSONB, nullable=True),
        sa.Column("dry_run", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_ctrl_decision_exc", "controller_decisions", ["exception_id", "controller_run_id"])

    # ── approval_requests ─────────────────────────────────────────────────────
    op.create_table(
        "approval_requests",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("exception_id", UUID(as_uuid=True), sa.ForeignKey("exceptions.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("decision_id", UUID(as_uuid=True), sa.ForeignKey("controller_decisions.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("requested_action", sa.String(128), nullable=False),
        sa.Column("amount", sa.Numeric(18, 4), nullable=True),
        sa.Column("risk_score", sa.Float(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="PENDING", index=True),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejected_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
    )
    op.create_index("ix_approval_status_requested", "approval_requests", ["status", "requested_at"])

    # ── controller_policies ───────────────────────────────────────────────────
    op.create_table(
        "controller_policies",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("policy_id", sa.String(128), nullable=False, index=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("configuration", JSONB, nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="ACTIVE", index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    )
    op.create_unique_constraint("uq_policy_id_version", "controller_policies", ["policy_id", "version"])
    op.create_index("ix_policy_active", "controller_policies", ["policy_id", "status"])

    # ── action_results ────────────────────────────────────────────────────────
    op.create_table(
        "action_results",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("decision_id", UUID(as_uuid=True), sa.ForeignKey("controller_decisions.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("exception_id", UUID(as_uuid=True), sa.ForeignKey("exceptions.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("action", sa.String(128), nullable=False),
        sa.Column("idempotency_key", sa.String(512), nullable=False, unique=True),
        sa.Column("status", sa.String(32), nullable=False, index=True),
        sa.Column("previous_state", sa.String(64), nullable=True),
        sa.Column("new_state", sa.String(64), nullable=True),
        sa.Column("policy_version", sa.String(64), nullable=True),
        sa.Column("executed_by", sa.String(128), nullable=False, server_default="system"),
        sa.Column("verified", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("verification_details", JSONB, nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("is_reversible", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("rolled_back", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("rolled_back_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # ── controller_config ─────────────────────────────────────────────────────
    op.create_table(
        "controller_config",
        sa.Column("key", sa.String(128), primary_key=True),
        sa.Column("value", JSONB, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("controller_config")
    op.drop_table("action_results")
    op.drop_table("controller_policies")
    op.drop_table("approval_requests")
    op.drop_table("controller_decisions")
    op.drop_table("controller_runs")
