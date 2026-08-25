"""Tests: Transaction endpoints."""

from tests.conftest import _get_token


def test_transaction_list(client, admin_user):
    token = _get_token(client, "admin@test.dev", "Admin@123")
    resp = client.get(
        "/api/v1/transactions",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data


def test_transaction_list_with_status_filter(client, admin_user):
    token = _get_token(client, "admin@test.dev", "Admin@123")
    resp = client.get(
        "/api/v1/transactions?status=SUCCESS",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200


def test_transaction_list_with_search(client, admin_user):
    token = _get_token(client, "admin@test.dev", "Admin@123")
    resp = client.get(
        "/api/v1/transactions?search=PAY",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200


def test_transaction_not_found(client, admin_user):
    import uuid
    token = _get_token(client, "admin@test.dev", "Admin@123")
    resp = client.get(
        f"/api/v1/transactions/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


def test_transaction_list_unauthenticated(client):
    resp = client.get("/api/v1/transactions")
    assert resp.status_code == 403
