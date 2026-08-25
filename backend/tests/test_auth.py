"""Tests: Authentication endpoints."""

from tests.conftest import _get_token


def test_login_success(client, admin_user):
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.dev", "password": "Admin@123"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "admin@test.dev"
    assert data["user"]["role"] == "ADMIN"


def test_login_invalid_password(client, admin_user):
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.dev", "password": "wrongpassword"},
    )
    assert resp.status_code == 401


def test_login_invalid_email(client):
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@test.dev", "password": "Admin@123"},
    )
    assert resp.status_code == 401


def test_get_me(client, admin_user):
    token = _get_token(client, "admin@test.dev", "Admin@123")
    resp = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["email"] == "admin@test.dev"


def test_get_me_no_token(client):
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 403  # HTTPBearer returns 403 when no token


def test_get_me_invalid_token(client):
    resp = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalidtoken"},
    )
    assert resp.status_code == 401
