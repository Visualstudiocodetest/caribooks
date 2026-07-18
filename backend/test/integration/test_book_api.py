import pytest
from  infrastructure.db import SessionLocal
from  infrastructure.models import Article
from  infrastructure import models
from sqlalchemy.sql import text


"""
Integration tests for FastAPI book endpoints.
"""
from fastapi.testclient import TestClient
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))
from  main import app
client = TestClient(app)

def test_create_and_get_book():
    # Register user and login
    import uuid
    uniq = uuid.uuid4().hex[:10]
    user = {
        "nom": "Int",
        "prenom": "User",
        "email": f"integration_{uniq}@example.com",
        "mot_de_passe": "password123",
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
    if token_resp.status_code != 200:
        # try to reset stored hash to expected one (tests may run against existing DB)
        from  infrastructure import crud_user
        db = SessionLocal()
        try:
            db_user = db.query(models.Utilisateur).filter(models.Utilisateur.email == user["email"]).first()
            if db_user:
                hashed = crud_user.get_password_hash(user["mot_de_passe"])
                db_user.mot_de_passe_hash = hashed
                db.commit()
        finally:
            db.close()
        token_resp = client.post("/auth/token", json={"username": user["email"], "password": user["mot_de_passe"]})
    assert token_resp.status_code == 200, token_resp.text
    token = token_resp.json()["access_token"]

    # Create
    payload = { # type: ignore
        "titre": "Integration Book",
        "isbn": f"ISBN_{uniq}",
        "auteur": "Integration Author",
        "editeur": "Integration Editor",
        "langue": "FR",
        "description": "Integration Desc",
        "image_link": "http://img.integration",
        "prix_chf": 20.0,
        "actif": True
    }
    response = client.post("/books", json=payload, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["titre"] == payload["titre"]
    # Get
    book_id = data["id_article"]
    response = client.get(f"/books/{book_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["isbn"] == payload["isbn"]
