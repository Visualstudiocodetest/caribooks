from __future__ import annotations

import uuid
from typing import Callable

import pytest
from fastapi.testclient import TestClient

from main import app
from infrastructure import models
from infrastructure.db import SessionLocal

@pytest.fixture(scope="session")
def client() -> TestClient:
    return TestClient(app)




@pytest.fixture(autouse=True)
def _reset_rate_limits():
    """Auth rate-limit state is process-global; clear it before every test so one
    test's registrations/logins don't push another over the per-IP/-account limit."""
    from services.rate_limit import clear_all_rate_limits

    clear_all_rate_limits()
    yield


@pytest.fixture()
def uniq() -> str:
    return uuid.uuid4().hex[:10]


@pytest.fixture()
def register_and_login(client: TestClient) -> Callable[[str, str], dict[str, str]]:
    def _fn(email: str, role: str = "user") -> dict[str, str]:
        user = {
            "nom": "Test",
            "prenom": "User",
            "email": email,
            "mot_de_passe": "password123",
        }
        r = client.post("/auth/register", json=user)
        assert r.status_code in (201, 400), r.text
        if role != "user":
            # Registration never accepts a role (privilege escalation fix) —
            # promote directly in the DB, the same way an admin would via PUT /users/{id}.
            db = SessionLocal()
            try:
                db.query(models.Utilisateur).filter(models.Utilisateur.email == email).update({"role": role})
                db.commit()
            finally:
                db.close()
        token_resp = client.post("/auth/token", json={"username": email, "password": user["mot_de_passe"]})
        assert token_resp.status_code == 200, token_resp.text
        token = token_resp.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    return _fn

