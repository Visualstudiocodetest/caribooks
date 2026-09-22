from __future__ import annotations

from fastapi.testclient import TestClient


def test_catalog_crud(client: TestClient, register_and_login, uniq: str):
    headers = register_and_login(f"catalog_{uniq}@example.com", role="admin")

    # EtatUsure
    r = client.post("/catalog/etat-usures", json={"libelle": f"Etat_{uniq}", "description": "d"}, headers=headers)
    assert r.status_code == 201, r.text
    etat = r.json()
    r = client.get(f"/catalog/etat-usures/{etat['id_etat_usure']}")
    assert r.status_code == 200
    r = client.put(f"/catalog/etat-usures/{etat['id_etat_usure']}", json={"description": "u"}, headers=headers)
    assert r.status_code == 200
    r = client.get("/catalog/etat-usures")
    assert r.status_code == 200

    # delete
    assert client.delete(f"/catalog/etat-usures/{etat['id_etat_usure']}", headers=headers).status_code == 204


def test_catalog_write_requires_admin(client: TestClient, register_and_login, uniq: str):
    user_headers = register_and_login(f"catalog_nonadmin_{uniq}@example.com", role="user")
    assert client.post(
        "/catalog/etat-usures",
        json={"libelle": "x", "description": "d"},
        headers=user_headers,
    ).status_code == 403

