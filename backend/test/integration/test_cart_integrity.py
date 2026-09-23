"""Regression tests for the cart/checkout bugs behind the reported symptoms:
a wrong order total at payment time ("le montant ne correspond pas"), and books
that stayed missing from the catalogue after a basket was abandoned.
"""
from __future__ import annotations

import threading

from fastapi.testclient import TestClient


def _make_book(client: TestClient, admin_headers: dict, isbn: str, prix_chf: float = 10.0) -> int:
    r = client.post(
        "/books/",
        json={"titre": f"Cart {isbn}", "isbn": isbn, "auteur": "A", "prix_chf": prix_chf, "actif": True},
        headers=admin_headers,
    )
    assert r.status_code == 201, r.text
    return r.json()["id_livre"]


def _set_stock(client: TestClient, admin_headers: dict, id_livre: int, uniq: str, qty: int) -> int:
    """Give `id_livre` exactly `qty` units on a dedicated source, dropping the
    implicit +1 row create_book adds so the quantity under test is exact."""
    for s in client.get("/stock/", headers=admin_headers).json():
        if s["id_livre"] == id_livre:
            client.delete(f"/stock/{s['id_stock']}", headers=admin_headers)
    src = client.post(
        "/stock/sources",
        json={"libelle": f"CartSrc_{uniq}_{id_livre}", "type_source": "WAREHOUSE", "description": "d"},
        headers=admin_headers,
    ).json()["id_source_stock"]
    r = client.post(
        "/stock/",
        json={"id_livre": id_livre, "id_source_stock": src, "quantite_disponible": qty, "quantite_reservee": 0},
        headers=admin_headers,
    )
    assert r.status_code == 201, r.text
    return src


def _availability(client: TestClient, id_livre: int) -> int:
    return client.get("/stock/availability", params={"livre_ids": str(id_livre)}).json().get(str(id_livre), 0)


def test_total_matches_lines_when_added_concurrently(client: TestClient, register_and_login, uniq: str):
    """montant_total_chf must equal sum(lines) + shipping even when the browser
    fires every add-to-cart request at once.

    This is the reported "le montant ne correspond pas" bug. Under MySQL's
    REPEATABLE READ each concurrent create_ligne summed only the lignes visible
    in its own snapshot, so the last writer stored a total missing the others'
    lines (observed: 11.00 CHF stored for a 31.00 CHF order). The stock locks
    also deadlocked, silently losing a line with an opaque HTTP 500.
    """
    headers = register_and_login(f"conc_{uniq}@example.com")
    admin_headers = register_and_login(f"concadm_{uniq}@example.com", role="admin")

    livres = []
    for i in range(4):
        lid = _make_book(client, admin_headers, f"C{uniq[:6]}{i}", prix_chf=10.0)
        _set_stock(client, admin_headers, lid, uniq, qty=5)
        livres.append(lid)

    cmd = client.post("/orders/commandes", json={"shipping_method": "CLICK_COLLECT"}, headers=headers).json()
    cid = cmd["id_commande"]

    failures: list[str] = []

    def add(id_livre: int) -> None:
        r = client.post(
            "/orders/lignes",
            json={"id_commande": cid, "id_livre": id_livre, "quantite": 1},
            headers=headers,
        )
        if r.status_code != 201:
            failures.append(f"{id_livre}: {r.status_code} {r.text}")

    threads = [threading.Thread(target=add, args=(lid,)) for lid in livres]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not failures, f"concurrent add-to-cart failed: {failures}"

    lignes = [ligne for ligne in client.get("/orders/lignes", headers=headers).json() if ligne["id_commande"] == cid]
    assert len(lignes) == 4, "every concurrently-added line must be persisted"

    commande = client.get(f"/orders/commandes/{cid}", headers=headers).json()
    expected = sum(ligne["prix_unitaire_chf"] * ligne["quantite"] for ligne in lignes) + commande["frais_port_chf"]
    assert commande["montant_total_chf"] == expected == 41.0


def test_adding_same_book_twice_merges_into_one_line(client: TestClient, register_and_login, uniq: str):
    """A re-submitted checkout must bump the existing ligne, not add a second
    row for the same book — the cart UI is keyed by id_livre and could neither
    show nor remove the duplicate, while the customer was charged for both."""
    headers = register_and_login(f"dup_{uniq}@example.com")
    admin_headers = register_and_login(f"dupadm_{uniq}@example.com", role="admin")

    lid = _make_book(client, admin_headers, f"D{uniq[:6]}", prix_chf=12.0)
    _set_stock(client, admin_headers, lid, uniq, qty=5)

    cid = client.post("/orders/commandes", json={"shipping_method": "CLICK_COLLECT"}, headers=headers).json()["id_commande"]
    for _ in range(2):
        assert client.post(
            "/orders/lignes", json={"id_commande": cid, "id_livre": lid, "quantite": 1}, headers=headers
        ).status_code == 201

    lignes = [ligne for ligne in client.get("/orders/lignes", headers=headers).json() if ligne["id_commande"] == cid]
    assert len(lignes) == 1
    assert lignes[0]["quantite"] == 2
    commande = client.get(f"/orders/commandes/{cid}", headers=headers).json()
    assert commande["montant_total_chf"] == 12.0 * 2 + 1.0


def test_new_cart_releases_the_previous_abandoned_one(client: TestClient, register_and_login, uniq: str):
    """Starting a new order must give back the stock the previous open cart held.

    Each click on « Passer commande » creates a commande; the abandoned one used
    to keep its reservation for the full 20-minute window, so the books the
    customer had just taken out of the basket stayed unavailable in the
    catalogue and a retry could fail with "Stock insuffisant".
    """
    headers = register_and_login(f"abandon_{uniq}@example.com")
    admin_headers = register_and_login(f"abandonadm_{uniq}@example.com", role="admin")

    lid = _make_book(client, admin_headers, f"A{uniq[:6]}", prix_chf=15.0)
    _set_stock(client, admin_headers, lid, uniq, qty=1)
    assert _availability(client, lid) == 1

    first = client.post("/orders/commandes", json={"shipping_method": "POST"}, headers=headers).json()
    assert client.post(
        "/orders/lignes", json={"id_commande": first["id_commande"], "id_livre": lid, "quantite": 1}, headers=headers
    ).status_code == 201
    assert _availability(client, lid) == 0, "the open cart holds the only copy"

    # The customer goes back to the basket and orders again.
    second = client.post("/orders/commandes", json={"shipping_method": "POST"}, headers=headers).json()
    assert client.get(f"/orders/commandes/{first['id_commande']}", headers=headers).json()["statut"] == "CANCELLED"
    assert _availability(client, lid) == 1, "the abandoned cart must release its reservation immediately"

    # …and the single copy is still buyable in the new cart.
    assert client.post(
        "/orders/lignes", json={"id_commande": second["id_commande"], "id_livre": lid, "quantite": 1}, headers=headers
    ).status_code == 201


def test_cancelling_a_cart_puts_the_books_back_on_sale(client: TestClient, register_and_login, uniq: str):
    """« Annuler la commande » must return the reserved copies to availability."""
    headers = register_and_login(f"cancel_{uniq}@example.com")
    admin_headers = register_and_login(f"canceladm_{uniq}@example.com", role="admin")

    lid = _make_book(client, admin_headers, f"X{uniq[:6]}", prix_chf=15.0)
    _set_stock(client, admin_headers, lid, uniq, qty=2)

    cid = client.post("/orders/commandes", json={"shipping_method": "POST"}, headers=headers).json()["id_commande"]
    client.post("/orders/lignes", json={"id_commande": cid, "id_livre": lid, "quantite": 2}, headers=headers)
    assert _availability(client, lid) == 0

    r = client.post(f"/orders/commandes/{cid}/cancel", headers=headers)
    assert r.status_code == 200, r.text
    assert r.json()["statut"] == "CANCELLED"
    assert _availability(client, lid) == 2


def test_removing_a_line_retotals_and_frees_stock(client: TestClient, register_and_login, uniq: str):
    """Deleting a ligne must drop its amount from the total — otherwise the
    commande is charged for a book the customer removed."""
    headers = register_and_login(f"rmline_{uniq}@example.com")
    admin_headers = register_and_login(f"rmlineadm_{uniq}@example.com", role="admin")

    keep = _make_book(client, admin_headers, f"K{uniq[:6]}", prix_chf=20.0)
    drop = _make_book(client, admin_headers, f"R{uniq[:6]}", prix_chf=30.0)
    _set_stock(client, admin_headers, keep, uniq, qty=3)
    _set_stock(client, admin_headers, drop, uniq, qty=3)

    cid = client.post("/orders/commandes", json={"shipping_method": "CLICK_COLLECT"}, headers=headers).json()["id_commande"]
    client.post("/orders/lignes", json={"id_commande": cid, "id_livre": keep, "quantite": 1}, headers=headers)
    dropped = client.post(
        "/orders/lignes", json={"id_commande": cid, "id_livre": drop, "quantite": 1}, headers=headers
    ).json()
    assert client.get(f"/orders/commandes/{cid}", headers=headers).json()["montant_total_chf"] == 51.0

    assert client.delete(f"/orders/lignes/{dropped['id_ligne_commande']}", headers=headers).status_code == 204
    assert client.get(f"/orders/commandes/{cid}", headers=headers).json()["montant_total_chf"] == 21.0
    assert _availability(client, drop) == 3, "the removed line's reservation must be released"


def test_cannot_open_a_payment_session_for_an_empty_cart(client: TestClient, register_and_login, uniq: str):
    """PostFinance rejects a zero-amount transaction with an opaque provider
    error; refuse here with something the customer can act on."""
    headers = register_and_login(f"emptypay_{uniq}@example.com")
    cid = client.post("/orders/commandes", json={"shipping_method": "POST"}, headers=headers).json()["id_commande"]

    r = client.post(
        "/orders/paiements/postfinance",
        json={"id_commande": cid, "reference_externe": f"local-{uniq}"},
        headers=headers,
    )
    assert r.status_code == 400, r.text
    assert "vide" in r.json()["detail"].lower()
