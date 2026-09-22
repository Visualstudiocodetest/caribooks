from __future__ import annotations

from fastapi.testclient import TestClient


def _make_book(client: TestClient, admin_headers: dict, uniq: str, prix_chf: float = 20.0) -> int:
    r = client.post(
        "/books/",
        json={
            "titre": "Stocked book",
            "isbn": f"ISBN_ST_{uniq}",
            "auteur": "Stock Author",
            "prix_chf": prix_chf,
            "actif": True,
        },
        headers=admin_headers,
    )
    assert r.status_code == 201, r.text
    id_livre = r.json()["id_livre"]

    # Creating a book always credits its initial +1 unit to a (possibly
    # auto-created) default SourceStock (see crud_book.create_book /
    # _add_one_to_stock) — the ISBN-scan intake flow this endpoint models.
    # Tests below then set up their own explicit stock quantities on their own
    # SourceStock, so drop that implicit row first to start from a clean
    # slate (matching the old bare-article fixture, which had zero stock).
    stock_rows = client.get("/stock/", headers=admin_headers).json()
    for s in stock_rows:
        if s["id_livre"] == id_livre:
            client.delete(f"/stock/{s['id_stock']}", headers=admin_headers)
    return id_livre


def test_stock_and_sources_crud(client: TestClient, register_and_login, uniq: str):
    headers = register_and_login(f"stock_{uniq}@example.com", role="admin")

    # create prerequisite: book
    id_livre = _make_book(client, headers, uniq)

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
            "id_livre": id_livre,
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
    livre in one call (replaces the frontend N+1 over the whole /stock/ list)."""
    headers = register_and_login(f"stockavail_{uniq}@example.com", role="admin")
    id_livre = _make_book(client, headers, uniq)
    r = client.post("/stock/sources", json={"libelle": f"AvSrc_{uniq}", "type_source": "WAREHOUSE", "description": "d"}, headers=headers)
    source_id = r.json()["id_source_stock"]
    client.post(
        "/stock/",
        json={"id_livre": id_livre, "id_source_stock": source_id, "quantite_disponible": 7, "quantite_reservee": 2},
        headers=headers,
    )

    r = client.get(f"/stock/availability?livre_ids={id_livre}")
    assert r.status_code == 200, r.text
    assert r.json()[str(id_livre)] == 5  # 7 - 2

    # unknown ids yield an empty map, not an error
    assert client.get("/stock/availability?livre_ids=99999999").json() == {}


def test_stock_write_requires_admin(client: TestClient, register_and_login, uniq: str):
    user_headers = register_and_login(f"stock_nonadmin_{uniq}@example.com", role="user")
    assert client.post(
        "/stock/sources", json={"libelle": "x", "type_source": "WAREHOUSE"}, headers=user_headers
    ).status_code == 403
    assert client.post("/stock/1/increment", json={"qty": 1}, headers=user_headers).status_code == 403
    assert client.post("/stock/1/decrement", json={"qty": 1}, headers=user_headers).status_code == 403
