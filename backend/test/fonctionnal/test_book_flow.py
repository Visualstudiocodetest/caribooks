import pytest
from  infrastructure.db import SessionLocal
from  infrastructure import models

"""
Functional test: Book CRUD flow via API
"""
from fastapi.testclient import TestClient
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))
from  main import app

client = TestClient(app)

def test_book_crud_flow():
    # Register + login (writes require auth)
    import uuid
    uniq_user = uuid.uuid4().hex[:10]
    import secrets
    test_password = secrets.token_urlsafe(12)
    user = {
        "nom": "Flow",
        "prenom": "User",
        "email": f"flow_{uniq_user}@example.com",
        "mot_de_passe": test_password,
    }
    r = client.post("/auth/register", json=user)
    assert r.status_code in (201, 400), r.text
    # Registration never grants a role (privilege escalation fix) — promote
    # directly in the DB, the same way an admin would via PUT /users/{id}.
    db = SessionLocal()
    try:
        db.query(models.Utilisateur).filter(models.Utilisateur.email == user["email"]).update({"role": "admin"})
        db.commit()
    finally:
        db.close()
    token_resp = client.post("/auth/token", json={"username": user["email"], "password": user["mot_de_passe"]})
    assert token_resp.status_code == 200, token_resp.text
    token = token_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create
    uniq = uuid.uuid4().hex[:10]
    payload = { # type: ignore
        "titre": "Flow Book",
        "isbn": f"FLOW_{uniq}",
        "auteur": "Flow Author",
        "editeur": "Flow Editor",
        "langue": "FR",
        "description": "Flow Desc",
        "image_link": "http://img.flow",
        "prix_chf": 30.0,
        "actif": True
    }
    r = client.post("/books/", json=payload, headers=headers)
    assert r.status_code == 201
    book = r.json()
    book_id = book["id_article"]
    # Update
    update = {"titre": "Flow Book Updated"}
    r = client.put(f"/books/{book_id}", json=update, headers=headers)
    assert r.status_code == 200
    assert r.json()["titre"] == "Flow Book Updated"
    # Delete
    r = client.delete(f"/books/{book_id}", headers=headers)
    assert r.status_code == 204
    # Get after delete
    r = client.get(f"/books/{book_id}")
    assert r.status_code == 404
