"""Invoice routes."""

import uuid
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser
from app.core.database import get_db
from app.models.audit_log import AuditAction
from app.models.invoice import InvoiceStatus
from app.schemas.invoice import InvoiceListResponse, InvoiceResponse
from app.services.audit_service import AuditService
from app.services.invoice_service import InvoiceService

router = APIRouter(prefix="/invoices", tags=["Invoices"])


@router.get("", response_model=InvoiceListResponse, summary="List invoices")
def list_invoices(
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    status: Optional[InvoiceStatus] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> InvoiceListResponse:
    return InvoiceService(db).list_invoices(
        inv_status=status, search=search, page=page, page_size=page_size,
    )


@router.get("/{invoice_id}", response_model=InvoiceResponse, summary="Get a single invoice")
def get_invoice(
    invoice_id: uuid.UUID,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> InvoiceResponse:
    result = InvoiceService(db).get_invoice(invoice_id)
    AuditService(db).log(
        action=AuditAction.VIEW_INVOICE,
        description=f"Invoice {invoice_id} viewed",
        user_id=current_user.id,
        entity_type="invoice",
        entity_id=str(invoice_id),
    )
    return result
