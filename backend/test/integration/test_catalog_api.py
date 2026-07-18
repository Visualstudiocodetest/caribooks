from __future__ import annotations

from fastapi.testclient import TestClient


def test_catalog_crud(client: TestClient, register_and_login, uniq: str):
    headers = register_and_login(f"catalog_{uniq}@example.com", role="admin")

    # TypeObjet
    r = client.post(
        "/catalog/type-objets",
        json={"libelle": "Livre", "code": f"BOOK_{uniq}", "description": "desc"},
        headers=headers,
    )
    assert r.status_code == 201, r.text
    type_objet = r.json()
    r = client.get(f"/catalog/type-objets/{type_objet['id_type_objet']}")
    assert r.status_code == 200
    r = client.put(
        f"/catalog/type-objets/{type_objet['id_type_objet']}",
        json={"description": "updated"},
        headers=headers,
    )
    assert r.status_code == 200
    r = client.get("/catalog/type-objets")
    assert r.status_code == 200

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

    # Categorie
    r = client.post("/catalog/categories", json={"libelle": f"Cat_{uniq}", "description": "d"}, headers=headers)
    assert r.status_code == 201, r.text
    cat = r.json()
    r = client.get(f"/catalog/categories/{cat['id_categorie']}")
    assert r.status_code == 200
    r = client.put(f"/catalog/categories/{cat['id_categorie']}", json={"description": "u"}, headers=headers)
    assert r.status_code == 200
    r = client.get("/catalog/categories")
    assert r.status_code == 200

    # delete
    assert client.delete(f"/catalog/categories/{cat['id_categorie']}", headers=headers).status_code == 204
    assert client.delete(f"/catalog/etat-usures/{etat['id_etat_usure']}", headers=headers).status_code == 204
    assert client.delete(f"/catalog/type-objets/{type_objet['id_type_objet']}", headers=headers).status_code == 204


def test_catalog_write_requires_admin(client: TestClient, register_and_login, uniq: str):
    user_headers = register_and_login(f"catalog_nonadmin_{uniq}@example.com", role="user")
    assert client.post(
        "/catalog/type-objets",
        json={"libelle": "x", "code": f"NA_{uniq}"},
        headers=user_headers,
    ).status_code == 403
    assert client.post(
        "/catalog/categories", json={"libelle": "x"}, headers=user_headers
    ).status_code == 403

