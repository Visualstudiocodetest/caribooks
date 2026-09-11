from __future__ import annotations

from fastapi.testclient import TestClient


def test_users_admin_only(client: TestClient, register_and_login, uniq: str):
    user_headers = register_and_login(f"normal_{uniq}@example.com", role="user")
    admin_headers = register_and_login(f"admin_{uniq}@example.com", role="admin")

    # non-admin forbidden
    r = client.get("/users/", headers=user_headers)
    assert r.status_code == 403

    # admin can list/get
    r = client.get("/users/", headers=admin_headers)
    assert r.status_code == 200, r.text
    users = r.json()
    assert isinstance(users, list)
    assert any(u["email"] == f"admin_{uniq}@example.com" for u in users)

    admin_user = next(u for u in users if u["email"] == f"admin_{uniq}@example.com")
    r = client.get(f"/users/{admin_user['id_utilisateur']}", headers=admin_headers)
    assert r.status_code == 200

