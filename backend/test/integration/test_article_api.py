from __future__ import annotations

from fastapi.testclient import TestClient


def test_article_crud(client: TestClient, register_and_login, uniq: str):
    headers = register_and_login(f"article_{uniq}@example.com", role="admin")

    # prerequisites
    r = client.post(
        "/catalog/type-objets",
        json={"libelle": "Livre", "code": f"ARTBOOK_{uniq}", "description": "d"},
        headers=headers,
    )
    assert r.status_code == 201, r.text
    type_id = r.json()["id_type_objet"]

    r = client.post("/catalog/etat-usures", json={"libelle": f"Neuf_{uniq}", "description": "d"}, headers=headers)
    assert r.status_code == 201, r.text
    etat_id = r.json()["id_etat_usure"]

    # create article
    payload = {
        "id_type_objet": type_id,
        "id_etat_usure": etat_id,
        "sku": f"SKU_{uniq}",
        "titre": "Article title",
        "description": "desc",
        "image_link": "http://img",
        "prix_chf": 12.5,
        "actif": True,
    }
    r = client.post("/articles/", json=payload, headers=headers)
    assert r.status_code == 201, r.text
    art = r.json()

    # public read
    assert client.get("/articles/").status_code == 200
    r = client.get(f"/articles/{art['id_article']}")
    assert r.status_code == 200

    # update
    r = client.put(
        f"/articles/{art['id_article']}",
        json={"titre": "Updated"},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    assert r.json()["titre"] == "Updated"

    # delete
    assert client.delete(f"/articles/{art['id_article']}", headers=headers).status_code == 204


def test_article_write_requires_admin(client: TestClient, register_and_login, uniq: str):
    user_headers = register_and_login(f"article_nonadmin_{uniq}@example.com", role="user")
    payload = {
        "id_type_objet": 1,
        "id_etat_usure": 1,
        "sku": f"SKU_NA_{uniq}",
        "titre": "Should not be creatable",
        "prix_chf": 5.0,
    }
    assert client.post("/articles/", json=payload, headers=user_headers).status_code == 403
    assert client.put("/articles/1", json={"titre": "x"}, headers=user_headers).status_code == 403
    assert client.delete("/articles/1", headers=user_headers).status_code == 403
