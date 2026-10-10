import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.security import verify_password, get_password_hash, create_access_token, decode_access_token

client = TestClient(app)


def test_password_hashing_argon2():
    raw = "SuperSecretSecurePass123!"
    h = get_password_hash(raw)
    assert h.startswith("$argon2")
    assert verify_password(raw, h) is True
    assert verify_password("WrongPassword!", h) is False


def test_jwt_token_creation_and_decoding():
    data = {"sub": "test@mechnova.com", "role": "admin", "uid": 42}
    token = create_access_token(data)
    decoded = decode_access_token(token)
    assert decoded is not None
    assert decoded["sub"] == "test@mechnova.com"
    assert decoded["role"] == "admin"
    assert decoded["uid"] == 42


def test_login_admin_success():
    resp = client.post("/api/auth/login", json={
        "email": "admin@mechnova.com",
        "password": "admin123",
        "role_tab": "admin"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["company_email"] == "admin@mechnova.com"
    assert data["user"]["role"] == "admin"
    assert data["user"]["name"] == "Marcus Vance"


def test_login_worker_success():
    resp = client.post("/api/auth/login", json={
        "email": "elena@mechnova.com",
        "password": "worker123",
        "role_tab": "worker"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["company_email"] == "elena@mechnova.com"
    assert data["user"]["role"] == "worker"
    assert data["user"]["company_id"] == "WRK-001"


def test_login_role_tab_mismatch_admin_on_worker_tab():
    resp = client.post("/api/auth/login", json={
        "email": "admin@mechnova.com",
        "password": "admin123",
        "role_tab": "worker"  # Admin attempting worker tab
    })
    assert resp.status_code == 403
    assert "Role Mismatch" in resp.json()["detail"]


def test_login_role_tab_mismatch_worker_on_admin_tab():
    resp = client.post("/api/auth/login", json={
        "email": "elena@mechnova.com",
        "password": "worker123",
        "role_tab": "admin"  # Worker attempting admin tab
    })
    assert resp.status_code == 403
    assert "Role Mismatch" in resp.json()["detail"]


def test_login_invalid_password():
    resp = client.post("/api/auth/login", json={
        "email": "admin@mechnova.com",
        "password": "wrong_password",
        "role_tab": "admin"
    })
    assert resp.status_code == 401
    assert "Invalid credentials" in resp.json()["detail"]


def test_login_nonexistent_email():
    resp = client.post("/api/auth/login", json={
        "email": "ghost@mechnova.com",
        "password": "anypassword",
        "role_tab": "worker"
    })
    assert resp.status_code == 401
    assert "Invalid credentials" in resp.json()["detail"]


def test_get_me_unauthorized():
    resp = client.get("/api/me")
    assert resp.status_code == 401


def test_get_me_authenticated():
    # Login as worker
    login_resp = client.post("/api/auth/login", json={
        "email": "david@mechnova.com",
        "password": "worker123",
        "role_tab": "worker"
    })
    token = login_resp.json()["access_token"]

    resp = client.get("/api/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    user = resp.json()
    assert user["company_email"] == "david@mechnova.com"
    assert user["name"] == "David Chen"
    assert user["role"] == "worker"


def test_role_restriction_worker_blocked_from_admin_route():
    # Login as worker
    login_resp = client.post("/api/auth/login", json={
        "email": "elena@mechnova.com",
        "password": "worker123",
        "role_tab": "worker"
    })
    worker_token = login_resp.json()["access_token"]

    # Try accessing admin-only endpoint
    resp = client.get("/api/me/admin-check", headers={"Authorization": f"Bearer {worker_token}"})
    assert resp.status_code == 403
    assert "Admin privileges required" in resp.json()["detail"]


def test_role_restriction_admin_granted_on_admin_route():
    # Login as admin
    login_resp = client.post("/api/auth/login", json={
        "email": "admin@mechnova.com",
        "password": "admin123",
        "role_tab": "admin"
    })
    admin_token = login_resp.json()["access_token"]

    # Access admin endpoint
    resp = client.get("/api/me/admin-check", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    assert resp.json()["admin_id"] == "ADM-001"
