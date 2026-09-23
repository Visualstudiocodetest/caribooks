"""Regression tests for privilege escalation and ownership boundaries.

Each test here corresponds to a hole that was actually reachable from an
ordinary logged-in account, not a hypothetical one.
"""
from __future__ import annotations

from fastapi.testclient import TestClient


def test_user_cannot_promote_self_to_admin(client: TestClient, register_and_login, uniq: str):
    """PUT /users/me must not accept `role`.

    It used to take the admin-facing UserUpdate schema, and crud_user.update_user
    applies every field it is handed — so any customer could send
    {"role": "admin"} against their own account and the very next request to an
    admin-only endpoint succeeded.
    """
    headers = register_and_login(f"escalate_{uniq}@example.com")
    assert client.get("/users/me", headers=headers).json()["role"] == "user"

    r = client.put("/users/me", json={"role": "admin"}, headers=headers)
    assert r.status_code == 200, r.text
    assert r.json()["role"] == "user", "PUT /users/me must ignore/reject `role`"

    # And the account really has no admin access, token refresh included.
    assert client.get("/users/me", headers=headers).json()["role"] == "user"
    assert client.get("/users/", headers=headers).status_code == 403


def test_self_update_keeps_allowed_fields(client: TestClient, register_and_login, uniq: str):
    """Dropping `role` must not break the fields a user legitimately edits."""
    headers = register_and_login(f"selfupd_{uniq}@example.com")
    r = client.put(
        "/users/me",
        json={"prenom": "Camille", "billing_city": "Genève", "billing_country": "Suisse"},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["prenom"] == "Camille"
    assert body["billing_city"] == "Genève"
    assert body["billing_country"] == "Suisse"


def test_self_update_rejects_taken_email(client: TestClient, register_and_login, uniq: str):
    """utilisateur.email is UNIQUE — a clash must be a 409, not an unhandled 500."""
    register_and_login(f"taken_{uniq}@example.com")
    headers = register_and_login(f"mover_{uniq}@example.com")

    r = client.put("/users/me", json={"email": f"taken_{uniq}@example.com"}, headers=headers)
    assert r.status_code == 409, r.text
    assert "déjà utilisée" in r.json()["detail"]


def test_admin_can_still_change_roles(client: TestClient, register_and_login, uniq: str):
    """The admin path (PUT /users/{id}) keeps `role` — only self-service lost it."""
    admin_headers = register_and_login(f"roleadm_{uniq}@example.com", role="admin")
    target_headers = register_and_login(f"roletarget_{uniq}@example.com")
    target_id = client.get("/users/me", headers=target_headers).json()["id_utilisateur"]

    r = client.put(f"/users/{target_id}", json={"role": "admin"}, headers=admin_headers)
    assert r.status_code == 200, r.text
    assert r.json()["role"] == "admin"
