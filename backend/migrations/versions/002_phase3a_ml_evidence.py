"""Phase 3A Migration — ML predictions, evidence documents, pgvector, extended audit actions.

Revision ID: 002
Revises: 001
Create Date: 2026-08-29 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Embedding dimension for all-MiniLM-L6-v2
EMBEDDING_DIM = 384


def upgrade() -> None:
    conn = op.get_bind()

    # ── pgvector extension ────────────────────────────────────────────────────
    conn.execute(sa.text("CREATE EXTENSION IF NOT EXISTS vector"))

    # ── Extend auditaction enum with Phase 3A values ──────────────────────────
    phase3_audit_actions = [
        "ML_ANALYSIS_REQUESTED",
        "ML_ANALYSIS_COMPLETED",
        "EVIDENCE_SEARCHED",
        "EVIDENCE_VIEWED",
        "INTELLIGENCE_CONTEXT_VIEWED",
    ]
    for val in phase3_audit_actions:
        conn.execute(
            sa.text(f"ALTER TYPE auditaction ADD VALUE IF NOT EXISTS '{val}'")
        )

    # ── Extend exceptiontype enum with FEE_VARIANCE and DATE_MISMATCH ─────────
    for val in ["FEE_VARIANCE", "DATE_MISMATCH"]:
        conn.execute(
            sa.text(f"ALTER TYPE exceptiontype ADD VALUE IF NOT EXISTS '{val}'")
        )

    # ── ML Model type enum ────────────────────────────────────────────────────
    modeltype_enum = postgresql.ENUM(
        "EXCEPTION_CLASSIFIER", "ANOMALY_DETECTOR",
        name="modeltype", create_type=False
    )
    modeltype_enum.create(conn, checkfirst=True)

    # ── ml_predictions table ──────────────────────────────────────────────────
    op.create_table(
        "ml_predictions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("merchant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("entity_type", sa.String(64), nullable=False),
        sa.Column("entity_id", sa.String(128), nullable=False),
        sa.Column(
            "model_type",
            sa.Enum("EXCEPTION_CLASSIFIER", "ANOMALY_DETECTOR", name="modeltype"),
            nullable=False,
        ),
        sa.Column("model_version", sa.String(64), nullable=False),
        sa.Column("prediction", sa.String(128), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("features_snapshot", postgresql.JSONB(), nullable=True),
        sa.Column("top_alternatives", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_ml_predictions_merchant_id", "ml_predictions", ["merchant_id"])
    op.create_index("ix_ml_predictions_entity_type", "ml_predictions", ["entity_type"])
    op.create_index("ix_ml_predictions_entity_id", "ml_predictions", ["entity_id"])
    op.create_index("ix_ml_predictions_model_type", "ml_predictions", ["model_type"])
    op.create_index("ix_ml_predictions_created_at", "ml_predictions", ["created_at"])
    op.create_index(
        "ix_ml_predictions_entity", "ml_predictions", ["entity_type", "entity_id"]
    )
    op.create_index(
        "ix_ml_predictions_merchant_model",
        "ml_predictions",
        ["merchant_id", "model_type"],
    )

    # ── evidence_source_type enum ─────────────────────────────────────────────
    evidence_source_enum = postgresql.ENUM(
        "TRANSACTION", "INVOICE", "SETTLEMENT", "BANK_TRANSACTION",
        "EXCEPTION", "FINANCE_RULE", "HISTORICAL_CASE",
        name="evidencesourcetype", create_type=False
    )
    evidence_source_enum.create(conn, checkfirst=True)

    evidence_trust_enum = postgresql.ENUM(
        "PRIMARY", "SECONDARY", "REFERENCE", "HISTORICAL",
        name="evidencetrustlevel", create_type=False
    )
    evidence_trust_enum.create(conn, checkfirst=True)

    # ── evidence_documents table ──────────────────────────────────────────────
    op.create_table(
        "evidence_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("merchant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "source_type",
            sa.Enum(
                "TRANSACTION", "INVOICE", "SETTLEMENT", "BANK_TRANSACTION",
                "EXCEPTION", "FINANCE_RULE", "HISTORICAL_CASE",
                name="evidencesourcetype",
            ),
            nullable=False,
        ),
        sa.Column("source_id", sa.String(128), nullable=True),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column(
            "trust_level",
            sa.Enum("PRIMARY", "SECONDARY", "REFERENCE", "HISTORICAL",
                    name="evidencetrustlevel"),
            nullable=False,
            server_default="SECONDARY",
        ),
        sa.Column("embedding_dim", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # Add the pgvector embedding column separately
    conn.execute(
        sa.text(
            f"ALTER TABLE evidence_documents "
            f"ADD COLUMN embedding vector({EMBEDDING_DIM})"
        )
    )

    op.create_index(
        "ix_evidence_merchant_id", "evidence_documents", ["merchant_id"]
    )
    op.create_index(
        "ix_evidence_source_type", "evidence_documents", ["source_type"]
    )
    op.create_index(
        "ix_evidence_source_id_col", "evidence_documents", ["source_id"]
    )
    op.create_index(
        "ix_evidence_created_at", "evidence_documents", ["created_at"]
    )
    op.create_index(
        "ix_evidence_merchant_source",
        "evidence_documents",
        ["merchant_id", "source_type"],
    )

    # IVFFlat index for approximate nearest-neighbour search (requires data first)
    # Created after data is loaded; skip here for migrations safety.
    # To create manually after seeding:
    #   CREATE INDEX ON evidence_documents USING ivfflat (embedding vector_cosine_ops) WITH (lists = 20);


def downgrade() -> None:
    op.drop_table("evidence_documents")
    op.drop_table("ml_predictions")

    for enum_name in ["evidencetrustlevel", "evidencesourcetype", "modeltype"]:
        op.execute(f"DROP TYPE IF EXISTS {enum_name}")

    # Note: removing values from a PostgreSQL enum requires recreating it.
    # For simplicity, we do not downgrade the auditaction/exceptiontype additions.
