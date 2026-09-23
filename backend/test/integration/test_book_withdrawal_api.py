"""Tests for withdrawing a book that is out of stock in every shop, and for the
stock bookkeeping around restocking and admin status changes."""
from __future__ import annotations

from fastapi.testclient import TestClient


def _make_book(client: TestClient, admin_headers: dict, isbn: str, prix_chf: float = 10.0) -> int:
    r = client.post(
        "/books/",
        json={"titre": f"Livre {isbn}", "isbn": isbn, "auteur": "A", "prix_chf": prix_chf, "actif": True},
        headers=admin_headers,
    )
    assert r.status_code == 201, r.text
    return r.json()["id_livre"]


def _clear_stock(client: TestClient, admin_headers: dict, id_livre: int) -> None:
    for s in client.get("/stock/", headers=admin_headers).json():
        if s["id_livre"] == id_livre:
            client.delete(f"/stock/{s['id_stock']}", headers=admin_headers)


def _set_stock(client: TestClient, admin_headers: dict, id_livre: int, uniq: str, qty: int) -> int:
    _clear_stock(client, admin_headers, id_livre)
    src = client.post(
        "/stock/sources",
        json={"libelle": f"WdSrc_{uniq}_{id_livre}", "type_source": "SHOP", "description": "d"},
        headers=admin_headers,
    ).json()["id_source_stock"]
    r = client.post(
        "/stock/",
        json={"id_livre": id_livre, "id_source_stock": src, "quantite_disponible": qty, "quantite_reservee": 0},
        headers=admin_headers,
    )
    assert r.status_code == 201, r.text
    return src


def test_withdraw_refused_while_stock_remains(client: TestClient, register_and_login, uniq: str):
    """Withdrawing a book that still has copies would delist something sellable."""
    admin_headers = register_and_login(f"wd1_{uniq}@example.com", role="admin")
    lid = _make_book(client, admin_headers, f"W1{uniq[:6]}")
    _set_stock(client, admin_headers, lid, uniq, qty=2)

    r = client.post(f"/books/{lid}/retirer", headers=admin_headers)
    assert r.status_code == 409, r.text
    assert "encore en stock" in r.json()["detail"]
    assert client.get(f"/books/{lid}").json()["actif"] is True


def test_withdraw_refused_while_reserved_in_a_cart(client: TestClient, register_and_login, uniq: str):
    """A copy held in somebody's open cart is still physically on the shelf.

    Its *availability* is 0 (disponible - reservee), so a guard written against
    availability would happily withdraw a book out from under a checkout in
    progress. physical_quantity is what the rule uses instead.
    """
    admin_headers = register_and_login(f"wd2a_{uniq}@example.com", role="admin")
    headers = register_and_login(f"wd2_{uniq}@example.com")
    lid = _make_book(client, admin_headers, f"W2{uniq[:6]}")
    _set_stock(client, admin_headers, lid, uniq, qty=1)

    cid = client.post("/orders/commandes", json={"shipping_method": "POST"}, headers=headers).json()["id_commande"]
    client.post("/orders/lignes", json={"id_commande": cid, "id_livre": lid, "quantite": 1}, headers=headers)

    assert client.get("/stock/availability", params={"livre_ids": str(lid)}).json().get(str(lid)) == 0

    r = client.post(f"/books/{lid}/retirer", headers=admin_headers)
    assert r.status_code == 409, r.text
    assert client.get(f"/books/{lid}").json()["actif"] is True


def test_withdraw_deletes_a_never_ordered_book(client: TestClient, register_and_login, uniq: str):
    """No order line references it, so the row can go away entirely."""
    admin_headers = register_and_login(f"wd3_{uniq}@example.com", role="admin")
    lid = _make_book(client, admin_headers, f"W3{uniq[:6]}")
    _clear_stock(client, admin_headers, lid)

    r = client.post(f"/books/{lid}/retirer", headers=admin_headers)
    assert r.status_code == 200, r.text
    assert r.json() is None
    assert client.get(f"/books/{lid}").status_code == 404


def test_withdraw_deactivates_a_previously_ordered_book(client: TestClient, register_and_login, uniq: str):
    """Its order lines must survive (accounting + ON DELETE RESTRICT), so the
    book is delisted rather than deleted."""
    admin_headers = register_and_login(f"wd4a_{uniq}@example.com", role="admin")
    headers = register_and_login(f"wd4_{uniq}@example.com")
    lid = _make_book(client, admin_headers, f"W4{uniq[:6]}")
    _set_stock(client, admin_headers, lid, uniq, qty=1)

    cid = client.post("/orders/commandes", json={"shipping_method": "POST"}, headers=headers).json()["id_commande"]
    client.post("/orders/lignes", json={"id_commande": cid, "id_livre": lid, "quantite": 1}, headers=headers)
    # Sold: finalize through the admin state machine, which consumes the stock.
    assert client.post(f"/orders/admin/commandes/{cid}/advance", headers=admin_headers).status_code == 200

    r = client.post(f"/books/{lid}/retirer", headers=admin_headers)
    assert r.status_code == 200, r.text
    assert r.json()["actif"] is False
    assert client.get(f"/books/{lid}").status_code == 200, "the row must be kept for the order line"
    lignes = client.get(f"/orders/admin/commandes/{cid}/lignes", headers=admin_headers).json()
    assert len(lignes) == 1


def test_delete_explains_why_an_ordered_book_cannot_be_deleted(client: TestClient, register_and_login, uniq: str):
    """ligne_commande.id_livre is ON DELETE RESTRICT: this used to be an
    unhandled IntegrityError (HTTP 500) with no hint about what to do."""
    admin_headers = register_and_login(f"wd5a_{uniq}@example.com", role="admin")
    headers = register_and_login(f"wd5_{uniq}@example.com")
    lid = _make_book(client, admin_headers, f"W5{uniq[:6]}")
    _set_stock(client, admin_headers, lid, uniq, qty=1)

    cid = client.post("/orders/commandes", json={"shipping_method": "POST"}, headers=headers).json()["id_commande"]
    client.post("/orders/lignes", json={"id_commande": cid, "id_livre": lid, "quantite": 1}, headers=headers)

    r = client.delete(f"/books/{lid}", headers=admin_headers)
    assert r.status_code == 409, r.text
    assert "Retirer de la vente" in r.json()["detail"]


def test_withdraw_requires_admin(client: TestClient, register_and_login, uniq: str):
    admin_headers = register_and_login(f"wd6a_{uniq}@example.com", role="admin")
    headers = register_and_login(f"wd6_{uniq}@example.com")
    lid = _make_book(client, admin_headers, f"W6{uniq[:6]}")
    assert client.post(f"/books/{lid}/retirer", headers=headers).status_code == 403


def test_restocking_a_sold_out_book_relists_it(client: TestClient, register_and_login, uniq: str):
    """finalize_commande sets actif = False once a title sells out; scanning a
    new copy back in must make it visible again, which nothing used to do."""
    admin_headers = register_and_login(f"wd7a_{uniq}@example.com", role="admin")
    isbn = f"W7{uniq[:6]}"
    lid = _make_book(client, admin_headers, isbn)
    assert client.put(f"/books/{lid}", json={"actif": False}, headers=admin_headers).status_code == 200

    # Re-scanning the same ISBN adds a unit to the existing book.
    again = client.post(
        "/books/",
        json={"titre": "Livre", "isbn": isbn, "auteur": "A", "prix_chf": 10.0, "actif": True},
        headers=admin_headers,
    )
    assert again.status_code == 201, again.text
    assert again.json()["id_livre"] == lid
    assert again.json()["actif"] is True


def test_admin_advance_consumes_the_cart_reservation(client: TestClient, register_and_login, uniq: str):
    """Marking an unpaid order PAID by hand used to only write the status
    column, leaving quantite_reservee held forever so the book never came back
    to the catalogue and was never actually deducted from stock either."""
    admin_headers = register_and_login(f"wd8a_{uniq}@example.com", role="admin")
    headers = register_and_login(f"wd8_{uniq}@example.com")
    lid = _make_book(client, admin_headers, f"W8{uniq[:6]}")
    _set_stock(client, admin_headers, lid, uniq, qty=3)

    cid = client.post("/orders/commandes", json={"shipping_method": "POST"}, headers=headers).json()["id_commande"]
    client.post("/orders/lignes", json={"id_commande": cid, "id_livre": lid, "quantite": 2}, headers=headers)

    r = client.post(f"/orders/admin/commandes/{cid}/advance", headers=admin_headers)
    assert r.status_code == 200, r.text
    assert r.json()["statut"] == "PAID"

    rows = [s for s in client.get("/stock/", headers=admin_headers).json() if s["id_livre"] == lid]
    assert sum(s["quantite_disponible"] for s in rows) == 1, "the sold units must leave physical stock"
    assert sum(s["quantite_reservee"] for s in rows) == 0, "the cart hold must be cleared"


def test_admin_set_status_cancel_releases_the_reservation(client: TestClient, register_and_login, uniq: str):
    admin_headers = register_and_login(f"wd9a_{uniq}@example.com", role="admin")
    headers = register_and_login(f"wd9_{uniq}@example.com")
    lid = _make_book(client, admin_headers, f"W9{uniq[:6]}")
    _set_stock(client, admin_headers, lid, uniq, qty=2)

    cid = client.post("/orders/commandes", json={"shipping_method": "POST"}, headers=headers).json()["id_commande"]
    client.post("/orders/lignes", json={"id_commande": cid, "id_livre": lid, "quantite": 2}, headers=headers)

    r = client.put(
        f"/orders/admin/commandes/{cid}/status", json={"statut": "CANCELLED"}, headers=admin_headers
    )
    assert r.status_code == 200, r.text
    avail = client.get("/stock/availability", params={"livre_ids": str(lid)}).json()
    assert avail.get(str(lid)) == 2


def test_admin_set_status_paid_to_cancelled_credits_sold_stock_back(
    client: TestClient, register_and_login, uniq: str
):
    """Regression for H-2: forcing a PAID order straight to CANCELLED/REFUNDED
    via the raw status override used to leave the sold units permanently
    deducted (no stock-side effect at all) and unrecoverable, since /refund
    then refuses because the order is no longer PAID."""
    admin_headers = register_and_login(f"wdH2a_{uniq}@example.com", role="admin")
    headers = register_and_login(f"wdH2_{uniq}@example.com")
    lid = _make_book(client, admin_headers, f"WH2{uniq[:6]}")
    _set_stock(client, admin_headers, lid, uniq, qty=3)

    cid = client.post("/orders/commandes", json={"shipping_method": "POST"}, headers=headers).json()["id_commande"]
    client.post("/orders/lignes", json={"id_commande": cid, "id_livre": lid, "quantite": 2}, headers=headers)

    r = client.post(f"/orders/admin/commandes/{cid}/advance", headers=admin_headers)
    assert r.status_code == 200, r.text
    assert r.json()["statut"] == "PAID"

    avail_paid = client.get("/stock/availability", params={"livre_ids": str(lid)}).json()
    assert avail_paid.get(str(lid)) == 1  # 3 in stock - 2 sold

    r = client.put(
        f"/orders/admin/commandes/{cid}/status", json={"statut": "CANCELLED"}, headers=admin_headers
    )
    assert r.status_code == 200, r.text

    avail_after = client.get("/stock/availability", params={"livre_ids": str(lid)}).json()
    assert avail_after.get(str(lid)) == 3, "sold stock must be credited back, not leaked forever"


def test_admin_set_status_paid_to_refunded_marks_payments_refunded(
    client: TestClient, register_and_login, uniq: str
):
    """Same H-2 fix, PAID -> REFUNDED transition: stock is credited back AND
    the order's payment records are marked REFUNDED, matching /refund's own
    behaviour instead of leaving them showing a stale success status."""
    admin_headers = register_and_login(f"wdH2ba_{uniq}@example.com", role="admin")
    headers = register_and_login(f"wdH2b_{uniq}@example.com")
    lid = _make_book(client, admin_headers, f"WH2B{uniq[:6]}")
    _set_stock(client, admin_headers, lid, uniq, qty=2)

    cid = client.post("/orders/commandes", json={"shipping_method": "POST"}, headers=headers).json()["id_commande"]
    client.post("/orders/lignes", json={"id_commande": cid, "id_livre": lid, "quantite": 1}, headers=headers)
    client.post(
        "/orders/paiements",
        json={"id_commande": cid, "reference_externe": f"REF_WDH2B_{uniq}"},
        headers=headers,
    )

    r = client.post(f"/orders/admin/commandes/{cid}/advance", headers=admin_headers)
    assert r.status_code == 200, r.text

    r = client.put(f"/orders/admin/commandes/{cid}/status", json={"statut": "REFUNDED"}, headers=admin_headers)
    assert r.status_code == 200, r.text
    assert r.json()["statut"] == "REFUNDED"

    avail_after = client.get("/stock/availability", params={"livre_ids": str(lid)}).json()
    assert avail_after.get(str(lid)) == 2

    paiements = client.get("/orders/paiements", headers=headers).json()
    own = [p for p in paiements if p["id_commande"] == cid]
    assert own and all(p["statut"] == "REFUNDED" for p in own)


def test_over_long_isbn_is_a_validation_error_not_a_crash(client: TestClient, register_and_login, uniq: str):
    admin_headers = register_and_login(f"wd10_{uniq}@example.com", role="admin")
    r = client.post(
        "/books/",
        json={"titre": "T", "isbn": "X" * 64, "auteur": "A", "prix_chf": 10.0, "actif": True},
        headers=admin_headers,
    )
    assert r.status_code == 422, r.text
