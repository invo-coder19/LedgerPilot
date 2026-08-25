"""Dashboard routes."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser
from app.core.database import get_db
from app.models.audit_log import AuditAction
from app.schemas.dashboard import (
    DashboardSummary,
    ExceptionTrendPoint,
    StatusDistributionItem,
    TransactionVolumePoint,
)
from app.services.audit_service import AuditService
from app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get(
    "/summary",
    response_model=DashboardSummary,
    summary="Key performance indicators for the dashboard",
)
def get_summary(
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> DashboardSummary:
    """Return aggregated KPI metrics computed from the database."""
    AuditService(db).log(
        action=AuditAction.VIEW_DASHBOARD,
        description="Dashboard summary viewed",
        user_id=current_user.id,
    )
    return DashboardService(db).get_summary()


@router.get(
    "/transaction-volume",
    response_model=list[TransactionVolumePoint],
    summary="Daily transaction volume for the last 30 days",
)
def get_transaction_volume(
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> list[TransactionVolumePoint]:
    return DashboardService(db).get_transaction_volume()


@router.get(
    "/status-distribution",
    response_model=list[StatusDistributionItem],
    summary="Transaction count grouped by status",
)
def get_status_distribution(
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> list[StatusDistributionItem]:
    return DashboardService(db).get_status_distribution()


@router.get(
    "/exception-trend",
    response_model=list[ExceptionTrendPoint],
    summary="Daily open vs resolved exception counts",
)
def get_exception_trend(
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> list[ExceptionTrendPoint]:
    return DashboardService(db).get_exception_trend()
