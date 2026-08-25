"""Tests: Dashboard endpoints."""

from tests.conftest import _get_token


def test_dashboard_summary_authenticated(client, admin_user):
    token = _get_token(client, "admin@test.dev", "Admin@123")
    resp = client.get(
        "/api/v1/dashboard/summary",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "total_transactions" in data
    assert "open_exceptions" in data
    assert "total_transaction_value" in data
    assert "total_settlement_value" in data


def test_dashboard_summary_unauthenticated(client):
    resp = client.get("/api/v1/dashboard/summary")
    assert resp.status_code == 403


def test_dashboard_transaction_volume(client, admin_user):
    token = _get_token(client, "admin@test.dev", "Admin@123")
    resp = client.get(
        "/api/v1/dashboard/transaction-volume",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_dashboard_status_distribution(client, admin_user):
    token = _get_token(client, "admin@test.dev", "Admin@123")
    resp = client.get(
        "/api/v1/dashboard/status-distribution",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
