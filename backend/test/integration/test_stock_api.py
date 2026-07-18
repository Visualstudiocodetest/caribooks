from __future__ import annotations

from fastapi.testclient import TestClient


def test_stock_and_sources_crud(client: TestClient, register_and_login, uniq: str):
    headers = register_and_login(f"stock_{uniq}@example.com", role="admin")

    # create prerequisites for stock: article
    r = client.post(
        "/catalog/type-objets",
        json={"libelle": "Livre", "code": f"STBOOK_{uniq}", "description": "d"},
        headers=headers,
    )
    type_id = r.json()["id_type_objet"]
    r = client.post("/catalog/etat-usures", json={"libelle": f"Etat_{uniq}", "description": "d"}, headers=headers)
    etat_id = r.json()["id_etat_usure"]
    r = client.post(
        "/articles/",
        json={
            "id_type_objet": type_id,
            "id_etat_usure": etat_id,
            "sku": f"SKU_ST_{uniq}",
            "titre": "Stocked article",
            "prix_chf": 10.0,
            "actif": True,
            "categorie_ids": [],
        },
        headers=headers,
    )
    assert r.status_code == 201, r.text
    article_id = r.json()["id_article"]

    # SourceStock
    r = client.post(
        "/stock/sources",
        json={"libelle": f"Source_{uniq}", "type_source": "WAREHOUSE", "description": "d"},
        headers=headers,
    )
    assert r.status_code == 201, r.text
    source = r.json()
    assert client.get("/stock/sources").status_code == 200
    assert client.get(f"/stock/sources/{source['id_source_stock']}").status_code == 200

    r = client.put(f"/stock/sources/{source['id_source_stock']}", json={"description": "u"}, headers=headers)
    assert r.status_code == 200

    # Stock
    r = client.post(
        "/stock/",
        json={
            "id_article": article_id,
            "id_source_stock": source["id_source_stock"],
            "quantite_disponible": 5,
            "quantite_reservee": 0,
        },
        headers=headers,
    )
    assert r.status_code == 201, r.text
    st = r.json()
    assert client.get("/stock/").status_code == 200
    assert client.get(f"/stock/{st['id_stock']}").status_code == 200

    r = client.put(f"/stock/{st['id_stock']}", json={"quantite_disponible": 7}, headers=headers)
    assert r.status_code == 200
    assert r.json()["quantite_disponible"] == 7

    assert client.delete(f"/stock/{st['id_stock']}", headers=headers).status_code == 204
    assert client.delete(f"/stock/sources/{source['id_source_stock']}", headers=headers).status_code == 204


def test_stock_availability_batch(client: TestClient, register_and_login, uniq: str):
    """The batched availability endpoint returns max(0, disponible - reservee) per
    article in one call (replaces the frontend N+1 over the whole /stock/ list)."""
    headers = register_and_login(f"stockavail_{uniq}@example.com", role="admin")
    r = client.post("/catalog/type-objets", json={"libelle": "Livre", "code": f"AVBOOK_{uniq}", "description": "d"}, headers=headers)
    type_id = r.json()["id_type_objet"]
    r = client.post("/catalog/etat-usures", json={"libelle": f"AvEtat_{uniq}", "description": "d"}, headers=headers)
    etat_id = r.json()["id_etat_usure"]
    r = client.post(
        "/articles/",
        json={"id_type_objet": type_id, "id_etat_usure": etat_id, "sku": f"SKU_AV_{uniq}", "titre": "Av", "prix_chf": 10.0, "actif": True, "categorie_ids": []},
        headers=headers,
    )
    article_id = r.json()["id_article"]
    r = client.post("/stock/sources", json={"libelle": f"AvSrc_{uniq}", "type_source": "WAREHOUSE", "description": "d"}, headers=headers)
    source_id = r.json()["id_source_stock"]
    client.post(
        "/stock/",
        json={"id_article": article_id, "id_source_stock": source_id, "quantite_disponible": 7, "quantite_reservee": 2},
        headers=headers,
    )

    r = client.get(f"/stock/availability?article_ids={article_id}")
    assert r.status_code == 200, r.text
    assert r.json()[str(article_id)] == 5  # 7 - 2

    # unknown ids yield an empty map, not an error
    assert client.get("/stock/availability?article_ids=99999999").json() == {}


def test_stock_write_requires_admin(client: TestClient, register_and_login, uniq: str):
    user_headers = register_and_login(f"stock_nonadmin_{uniq}@example.com", role="user")
    assert client.post(
        "/stock/sources", json={"libelle": "x", "type_source": "WAREHOUSE"}, headers=user_headers
    ).status_code == 403
    assert client.post("/stock/1/increment", json={"qty": 1}, headers=user_headers).status_code == 403
    assert client.post("/stock/1/decrement", json={"qty": 1}, headers=user_headers).status_code == 403

