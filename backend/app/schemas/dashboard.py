"""Dashboard Pydantic schemas."""

from decimal import Decimal
from pydantic import BaseModel


class DashboardSummary(BaseModel):
    total_transactions: int
    matched_transactions: int
    unmatched_transactions: int
    open_exceptions: int
    resolved_exceptions: int
    total_transaction_value: Decimal
    total_settlement_value: Decimal


class TransactionVolumePoint(BaseModel):
    date: str
    count: int
    amount: Decimal


class StatusDistributionItem(BaseModel):
    status: str
    count: int


class ExceptionTrendPoint(BaseModel):
    date: str
    open: int
    resolved: int
