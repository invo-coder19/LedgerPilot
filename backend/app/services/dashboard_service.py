"""Dashboard service — computes KPI metrics from the database."""

import math
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.transaction import TransactionStatus
from app.models.exception import ExceptionStatus
from app.repositories.exception_repository import ExceptionRepository
from app.repositories.transaction_repository import TransactionRepository
from app.repositories.settlement_repository import SettlementRepository
from app.schemas.dashboard import (
    DashboardSummary,
    ExceptionTrendPoint,
    StatusDistributionItem,
    TransactionVolumePoint,
)


class DashboardService:
    def __init__(self, db: Session) -> None:
        self.tx_repo = TransactionRepository(db)
        self.exc_repo = ExceptionRepository(db)
        self.settlement_repo = SettlementRepository(db)

    def get_summary(self) -> DashboardSummary:
        status_counts = self.tx_repo.count_by_status()
        total_transactions = sum(status_counts.values())
        # "matched" = SUCCESS + REFUNDED + PARTIAL_REFUND for Phase 1
        matched = (
            status_counts.get(TransactionStatus.SUCCESS, 0)
            + status_counts.get(TransactionStatus.REFUNDED, 0)
            + status_counts.get(TransactionStatus.PARTIAL_REFUND, 0)
        )
        unmatched = total_transactions - matched

        exc_counts = self.exc_repo.count_by_status()
        open_exceptions = exc_counts.get(ExceptionStatus.OPEN, 0) + exc_counts.get(ExceptionStatus.IN_REVIEW, 0)
        resolved_exceptions = exc_counts.get(ExceptionStatus.RESOLVED, 0)

        total_tx_value = Decimal(str(self.tx_repo.sum_amount()))
        total_settlement_value = Decimal(str(self.settlement_repo.sum_amount()))

        return DashboardSummary(
            total_transactions=total_transactions,
            matched_transactions=matched,
            unmatched_transactions=unmatched,
            open_exceptions=open_exceptions,
            resolved_exceptions=resolved_exceptions,
            total_transaction_value=total_tx_value,
            total_settlement_value=total_settlement_value,
        )

    def get_transaction_volume(self) -> list[TransactionVolumePoint]:
        rows = self.tx_repo.volume_over_time(days=30)
        return [
            TransactionVolumePoint(date=r["date"], count=r["count"], amount=Decimal(str(r["amount"])))
            for r in rows
        ]

    def get_status_distribution(self) -> list[StatusDistributionItem]:
        counts = self.tx_repo.count_by_status()
        return [StatusDistributionItem(status=k, count=v) for k, v in counts.items()]

    def get_exception_trend(self) -> list[ExceptionTrendPoint]:
        rows = self.exc_repo.trend_over_time()
        # Pivot by date
        pivot: dict[str, dict] = {}
        for r in rows:
            d = r["date"]
            if d not in pivot:
                pivot[d] = {"open": 0, "resolved": 0}
            if r["status"] in (str(ExceptionStatus.OPEN), str(ExceptionStatus.IN_REVIEW)):
                pivot[d]["open"] += r["count"]
            elif r["status"] == str(ExceptionStatus.RESOLVED):
                pivot[d]["resolved"] += r["count"]
        return [
            ExceptionTrendPoint(date=d, open=v["open"], resolved=v["resolved"])
            for d, v in sorted(pivot.items())
        ]
