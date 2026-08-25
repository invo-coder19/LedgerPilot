"""Tests: Exception endpoints including RBAC."""

import uuid
from decimal import Decimal
from datetime import datetime, timezone

import pytest

from app.models.exception import ExceptionSeverity, ExceptionStatus, ExceptionType
from app.models.exception import Exception as FinancialException
from app.models.merchant import Merchant
from tests.conftest import TestingSessionLocal, _create_user, _get_token
from app.models.user import Role


def _create_merchant_and_exception(db) -> tuple:
    merchant = db.query(Merchant).first()
    if not merchant:
        merchant = Merchant(
            name="Test", business_name="Test Merchant", email="test@test.com",
            currency="INR", timezone="Asia/Kolkata",
        )
        db.add(merchant)
        db.commit()
        db.refresh(merchant)

    exc = FinancialException(
        merchant_id=merchant.id,
        source_type="transaction",
        source_id="PAY001",
        exception_type=ExceptionType.AMOUNT_MISMATCH,
        severity=ExceptionSeverity.HIGH,
        amount=Decimal("10000.00"),
        description="Test exception",
        status=ExceptionStatus.OPEN,
    )
    db.add(exc)
    db.commit()
    db.refresh(exc)
    return merchant, exc


def test_exception_list(client, admin_user):
    token = _get_token(client, "admin@test.dev", "Admin@123")
    resp = client.get(
        "/api/v1/exceptions",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data


def test_exception_update_as_admin(client, admin_user):
    db = TestingSessionLocal()
    _, exc = _create_merchant_and_exception(db)
    db.close()

    token = _get_token(client, "admin@test.dev", "Admin@123")
    resp = client.patch(
        f"/api/v1/exceptions/{exc.id}",
        json={"status": "IN_REVIEW"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "IN_REVIEW"


def test_exception_update_as_viewer_forbidden(client, viewer_user):
    db = TestingSessionLocal()
    _, exc = _create_merchant_and_exception(db)
    db.close()

    token = _get_token(client, "viewer@test.dev", "Viewer@123")
    resp = client.patch(
        f"/api/v1/exceptions/{exc.id}",
        json={"status": "RESOLVED"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


def test_exception_not_found(client, admin_user):
    token = _get_token(client, "admin@test.dev", "Admin@123")
    resp = client.get(
        f"/api/v1/exceptions/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


def test_exception_filter_by_status(client, admin_user):
    token = _get_token(client, "admin@test.dev", "Admin@123")
    resp = client.get(
        "/api/v1/exceptions?status=OPEN",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
