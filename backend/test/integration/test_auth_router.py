from __future__ import annotations

from fastapi.testclient import TestClient


def test_register_ignores_client_supplied_role(client: TestClient, uniq: str):
    """The privilege-escalation fix: role must never be accepted from the
    registration payload, regardless of what the client sends."""
    email = f"escalate_{uniq}@example.com"
    r = client.post(
        "/auth/register",
        json={
            "nom": "Test",
            "prenom": "User",
            "email": email,
            "mot_de_passe": "password123",
            "role": "admin",
        },
    )
    assert r.status_code == 201, r.text
    assert r.json()["role"] == "user"

    token_resp = client.post("/auth/token", json={"username": email, "password": "password123"})
    assert token_resp.status_code == 200
    token = token_resp.json()["access_token"]

    # the resulting account must NOT have admin access
    r = client.get("/users/", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403


def test_login_wrong_password_rejected(client: TestClient, register_and_login, uniq: str):
    email = f"wrongpass_{uniq}@example.com"
    register_and_login(email)
    r = client.post("/auth/token", json={"username": email, "password": "not-the-password"})
    assert r.status_code == 401


def test_login_nonexistent_user_rejected(client: TestClient, uniq: str):
    r = client.post(
        "/auth/token",
        json={"username": f"doesnotexist_{uniq}@example.com", "password": "whatever123"},
    )
    assert r.status_code == 401


def test_protected_route_rejects_missing_and_garbage_token(client: TestClient):
    r = client.get("/users/me")
    assert r.status_code in (401, 403)  # HTTPBearer with no header

    r = client.get("/users/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert r.status_code == 401


def test_duplicate_user_creation_endpoint_is_gone(client: TestClient, uniq: str):
    """The unauthenticated POST /users/ endpoint (a second privilege-escalation
    path, duplicating /auth/register with no auth and no schema validation)
    has been removed entirely."""
    r = client.post(
        "/users/",
        json={"nom": "x", "prenom": "x", "email": f"gone_{uniq}@example.com", "mot_de_passe": "x", "role": "admin"},
    )
    assert r.status_code in (404, 405)


def test_google_auth_rejects_invalid_credential(client: TestClient):
    r = client.post("/auth/google", json={"credential": "not-a-real-google-jwt"})
    assert r.status_code == 400


def test_login_is_rate_limited_per_account(client: TestClient, register_and_login, uniq: str):
    email = f"ratelimited_{uniq}@example.com"
    register_and_login(email)
    for _ in range(10):
        r = client.post("/auth/token", json={"username": email, "password": "wrong-password"})
        assert r.status_code == 401
    r = client.post("/auth/token", json={"username": email, "password": "wrong-password"})
    assert r.status_code == 429
