"""Initial schema — Phase 1 tables.

Revision ID: 001
Revises: 
Create Date: 2026-08-25 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── ENUMS ─────────────────────────────────────────────────────────────────
    role_enum = postgresql.ENUM(
        "ADMIN", "FINANCE_MANAGER", "FINANCE_ANALYST", "VIEWER",
        name="role", create_type=False
    )
    role_enum.create(op.get_bind(), checkfirst=True)

    transaction_status_enum = postgresql.ENUM(
        "SUCCESS", "FAILED", "REFUNDED", "PARTIAL_REFUND", "PENDING",
        name="transactionstatus", create_type=False
    )
    transaction_status_enum.create(op.get_bind(), checkfirst=True)

    invoice_status_enum = postgresql.ENUM(
        "ISSUED", "PAID", "PARTIALLY_PAID", "OVERDUE", "CANCELLED",
        name="invoicestatus", create_type=False
    )
    invoice_status_enum.create(op.get_bind(), checkfirst=True)

    settlement_status_enum = postgresql.ENUM(
        "PENDING", "PROCESSED", "FAILED",
        name="settlementstatus", create_type=False
    )
    settlement_status_enum.create(op.get_bind(), checkfirst=True)

    bank_transaction_type_enum = postgresql.ENUM(
        "CREDIT", "DEBIT",
        name="banktransactiontype", create_type=False
    )
    bank_transaction_type_enum.create(op.get_bind(), checkfirst=True)

    exception_type_enum = postgresql.ENUM(
        "AMOUNT_MISMATCH", "MISSING_INVOICE", "MISSING_SETTLEMENT",
        "DUPLICATE", "REFUND_MISMATCH", "UNKNOWN",
        name="exceptiontype", create_type=False
    )
    exception_type_enum.create(op.get_bind(), checkfirst=True)

    exception_severity_enum = postgresql.ENUM(
        "LOW", "MEDIUM", "HIGH", "CRITICAL",
        name="exceptionseverity", create_type=False
    )
    exception_severity_enum.create(op.get_bind(), checkfirst=True)

    exception_status_enum = postgresql.ENUM(
        "OPEN", "IN_REVIEW", "RESOLVED", "DISMISSED",
        name="exceptionstatus", create_type=False
    )
    exception_status_enum.create(op.get_bind(), checkfirst=True)

    audit_action_enum = postgresql.ENUM(
        "LOGIN", "LOGOUT", "VIEW_TRANSACTION", "VIEW_INVOICE",
        "VIEW_SETTLEMENT", "VIEW_BANK_TRANSACTION", "VIEW_EXCEPTION",
        "UPDATE_EXCEPTION", "APPROVE_ACTION", "REJECT_ACTION",
        "VIEW_AUDIT_LOG", "VIEW_DASHBOARD",
        name="auditaction", create_type=False
    )
    audit_action_enum.create(op.get_bind(), checkfirst=True)

    # ── MERCHANTS ─────────────────────────────────────────────────────────────
    op.create_table(
        "merchants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("business_name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("currency", sa.String(10), nullable=False, server_default="INR"),
        sa.Column("timezone", sa.String(64), nullable=False, server_default="Asia/Kolkata"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_merchants_email", "merchants", ["email"])

    # ── USERS ─────────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("role", sa.Enum("ADMIN", "FINANCE_MANAGER", "FINANCE_ANALYST", "VIEWER", name="role"), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # ── TRANSACTIONS ──────────────────────────────────────────────────────────
    op.create_table(
        "transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("merchant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("merchants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("payment_id", sa.String(128), nullable=False),
        sa.Column("order_id", sa.String(128), nullable=False),
        sa.Column("customer_id", sa.String(128), nullable=True),
        sa.Column("amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("fee", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("tax", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("status", sa.Enum("SUCCESS", "FAILED", "REFUNDED", "PARTIAL_REFUND", "PENDING", name="transactionstatus"), nullable=False),
        sa.Column("payment_method", sa.String(64), nullable=True),
        sa.Column("transaction_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_transactions_merchant_id", "transactions", ["merchant_id"])
    op.create_index("ix_transactions_payment_id", "transactions", ["payment_id"])
    op.create_index("ix_transactions_order_id", "transactions", ["order_id"])
    op.create_index("ix_transactions_status", "transactions", ["status"])
    op.create_index("ix_transactions_status_created_at", "transactions", ["status", "created_at"])
    op.create_index("ix_transactions_merchant_created_at", "transactions", ["merchant_id", "created_at"])

    # ── INVOICES ──────────────────────────────────────────────────────────────
    op.create_table(
        "invoices",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("merchant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("merchants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("invoice_id", sa.String(128), nullable=False),
        sa.Column("customer_id", sa.String(128), nullable=True),
        sa.Column("amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("tax", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("status", sa.Enum("ISSUED", "PAID", "PARTIALLY_PAID", "OVERDUE", "CANCELLED", name="invoicestatus"), nullable=False),
        sa.Column("invoice_date", sa.Date(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("payment_reference", sa.String(128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_invoices_merchant_id", "invoices", ["merchant_id"])
    op.create_index("ix_invoices_invoice_id", "invoices", ["invoice_id"])
    op.create_index("ix_invoices_status", "invoices", ["status"])
    op.create_index("ix_invoices_merchant_status", "invoices", ["merchant_id", "status"])

    # ── SETTLEMENTS ───────────────────────────────────────────────────────────
    op.create_table(
        "settlements",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("merchant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("merchants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("settlement_id", sa.String(128), nullable=False),
        sa.Column("payment_id", sa.String(128), nullable=False),
        sa.Column("settlement_amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("fee", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("settlement_date", sa.Date(), nullable=False),
        sa.Column("status", sa.Enum("PENDING", "PROCESSED", "FAILED", name="settlementstatus"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_settlements_merchant_id", "settlements", ["merchant_id"])
    op.create_index("ix_settlements_settlement_id", "settlements", ["settlement_id"])
    op.create_index("ix_settlements_payment_id", "settlements", ["payment_id"])
    op.create_index("ix_settlements_status", "settlements", ["status"])
    op.create_index("ix_settlements_merchant_status", "settlements", ["merchant_id", "status"])

    # ── BANK TRANSACTIONS ─────────────────────────────────────────────────────
    op.create_table(
        "bank_transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("merchant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("merchants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("bank_transaction_id", sa.String(128), nullable=False),
        sa.Column("reference", sa.String(128), nullable=True),
        sa.Column("amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("transaction_type", sa.Enum("CREDIT", "DEBIT", name="banktransactiontype"), nullable=False),
        sa.Column("transaction_date", sa.Date(), nullable=False),
        sa.Column("description", sa.String(512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_bank_transactions_merchant_id", "bank_transactions", ["merchant_id"])
    op.create_index("ix_bank_transactions_bank_transaction_id", "bank_transactions", ["bank_transaction_id"])
    op.create_index("ix_bank_transactions_transaction_type", "bank_transactions", ["transaction_type"])
    op.create_index("ix_bank_transactions_merchant_date", "bank_transactions", ["merchant_id", "transaction_date"])

    # ── EXCEPTIONS ────────────────────────────────────────────────────────────
    op.create_table(
        "exceptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("merchant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("merchants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_type", sa.String(64), nullable=False),
        sa.Column("source_id", sa.String(128), nullable=False),
        sa.Column("exception_type", sa.Enum("AMOUNT_MISMATCH", "MISSING_INVOICE", "MISSING_SETTLEMENT", "DUPLICATE", "REFUND_MISMATCH", "UNKNOWN", name="exceptiontype"), nullable=False),
        sa.Column("severity", sa.Enum("LOW", "MEDIUM", "HIGH", "CRITICAL", name="exceptionseverity"), nullable=False),
        sa.Column("amount", sa.Numeric(18, 4), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.Enum("OPEN", "IN_REVIEW", "RESOLVED", "DISMISSED", name="exceptionstatus"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_exceptions_merchant_id", "exceptions", ["merchant_id"])
    op.create_index("ix_exceptions_exception_type", "exceptions", ["exception_type"])
    op.create_index("ix_exceptions_severity", "exceptions", ["severity"])
    op.create_index("ix_exceptions_status", "exceptions", ["status"])
    op.create_index("ix_exceptions_merchant_status", "exceptions", ["merchant_id", "status"])
    op.create_index("ix_exceptions_merchant_severity", "exceptions", ["merchant_id", "severity"])

    # ── AUDIT LOGS ────────────────────────────────────────────────────────────
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("merchant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("merchants.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action", sa.Enum(
            "LOGIN", "LOGOUT", "VIEW_TRANSACTION", "VIEW_INVOICE",
            "VIEW_SETTLEMENT", "VIEW_BANK_TRANSACTION", "VIEW_EXCEPTION",
            "UPDATE_EXCEPTION", "APPROVE_ACTION", "REJECT_ACTION",
            "VIEW_AUDIT_LOG", "VIEW_DASHBOARD",
            name="auditaction"
        ), nullable=False),
        sa.Column("entity_type", sa.String(64), nullable=True),
        sa.Column("entity_id", sa.String(128), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"])
    op.create_index("ix_audit_logs_merchant_id", "audit_logs", ["merchant_id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("exceptions")
    op.drop_table("bank_transactions")
    op.drop_table("settlements")
    op.drop_table("invoices")
    op.drop_table("transactions")
    op.drop_table("users")
    op.drop_table("merchants")

    # Drop enums
    for enum_name in [
        "auditaction", "exceptionstatus", "exceptionseverity", "exceptiontype",
        "banktransactiontype", "settlementstatus", "invoicestatus",
        "transactionstatus", "role",
    ]:
        op.execute(f"DROP TYPE IF EXISTS {enum_name}")
