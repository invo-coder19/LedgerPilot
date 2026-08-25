"""Tests: Audit log endpoints."""

from tests.conftest import _get_token


def test_audit_log_list_as_admin(client, admin_user):
    token = _get_token(client, "admin@test.dev", "Admin@123")
    resp = client.get(
        "/api/v1/audit-logs",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data


def test_audit_log_list_as_viewer_forbidden(client, viewer_user):
    token = _get_token(client, "viewer@test.dev", "Viewer@123")
    resp = client.get(
        "/api/v1/audit-logs",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


def test_audit_log_created_on_login(client, admin_user):
    """Verify a login event creates an audit log entry."""
    token = _get_token(client, "admin@test.dev", "Admin@123")
    resp = client.get(
        "/api/v1/audit-logs?action=LOGIN",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
