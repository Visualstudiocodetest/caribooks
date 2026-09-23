from __future__ import annotations

from fastapi.testclient import TestClient

from infrastructure import models
from infrastructure.db import SessionLocal


def _make_book(client: TestClient, admin_headers: dict, uniq: str, prix_chf: float = 20.0) -> int:
    r = client.post(
        "/books/",
        json={
            "titre": "Deletion test book",
            "isbn": f"ISBN_DEL_{uniq}",
            "auteur": "Deletion Author",
            "prix_chf": prix_chf,
            "actif": True,
        },
        headers=admin_headers,
    )
    assert r.status_code == 201, r.text
    id_livre = r.json()["id_livre"]

    # Creating a book always credits its initial +1 unit to a (possibly
    # auto-created) default SourceStock (see crud_book.create_book /
    # _add_one_to_stock) — drop that implicit row so _make_stock's caller
    # starts from a clean slate (matching the old bare-article fixture,
    # which had zero stock).
    stock_rows = client.get("/stock/", headers=admin_headers).json()
    for s in stock_rows:
        if s["id_livre"] == id_livre:
            client.delete(f"/stock/{s['id_stock']}", headers=admin_headers)
    return id_livre


def _make_stock(client: TestClient, admin_headers: dict, uniq: str, id_livre: int, qty: int = 10) -> None:
    r = client.post(
        "/stock/sources",
        json={"libelle": f"SourceDel_{uniq}", "type_source": "WAREHOUSE", "description": "d"},
        headers=admin_headers,
    )
    assert r.status_code == 201, r.text
    source_id = r.json()["id_source_stock"]
    r = client.post(
        "/stock/",
        json={
            "id_livre": id_livre,
            "id_source_stock": source_id,
            "quantite_disponible": qty,
            "quantite_reservee": 0,
        },
        headers=admin_headers,
    )
    assert r.status_code == 201, r.text


def _make_commande(client: TestClient, headers: dict, uniq: str, suffix: str = "") -> dict:
    r = client.post(
        "/orders/commandes",
        json={"numero_commande": f"CMDDEL_{uniq}{suffix}", "shipping_method": "POST"},
        headers=headers,
    )
    assert r.status_code == 201, r.text
    return r.json()


def _set_status(client: TestClient, admin_headers: dict, id_commande: int, statut: str) -> None:
    r = client.put(
        f"/orders/admin/commandes/{id_commande}/status", json={"statut": statut}, headers=admin_headers
    )
    assert r.status_code == 200, r.text


def _user_row(id_utilisateur: int) -> models.Utilisateur:
    db = SessionLocal()
    try:
        return db.query(models.Utilisateur).filter(models.Utilisateur.id_utilisateur == id_utilisateur).first()
    finally:
        db.close()


def _get_user_id(client: TestClient, admin_headers: dict, email: str) -> int:
    users = client.get("/users/", headers=admin_headers).json()
    return next(u["id_utilisateur"] for u in users if u["email"] == email)


def test_delete_me_succeeds_with_no_orders(client: TestClient, register_and_login, uniq: str):
    email = f"del_none_{uniq}@example.com"
    headers = register_and_login(email)
    admin_headers = register_and_login(f"del_admin1_{uniq}@example.com", role="admin")
    uid = _get_user_id(client, admin_headers, email)

    r = client.delete("/users/me", headers=headers)
    assert r.status_code == 204, r.text

    row = _user_row(uid)
    assert row.email == f"deleted-{uid}@anonymized.invalid"
    assert row.mot_de_passe_hash is None


def test_delete_me_refused_with_open_order(client: TestClient, register_and_login, uniq: str):
    email = f"del_open_{uniq}@example.com"
    headers = register_and_login(email)
    admin_headers = register_and_login(f"del_admin2_{uniq}@example.com", role="admin")
    uid = _get_user_id(client, admin_headers, email)

    # A freshly created commande is CREATED, one of the blocking statuses.
    _make_commande(client, headers, uniq)

    r = client.delete("/users/me", headers=headers)
    assert r.status_code == 409, r.text

    row = _user_row(uid)
    assert row.email == email  # untouched


def test_delete_me_refused_with_paid_not_yet_finished_order(client: TestClient, register_and_login, uniq: str):
    email = f"del_paid_{uniq}@example.com"
    headers = register_and_login(email)
    admin_headers = register_and_login(f"del_admin3_{uniq}@example.com", role="admin")
    uid = _get_user_id(client, admin_headers, email)

    cmd = _make_commande(client, headers, uniq)
    _set_status(client, admin_headers, cmd["id_commande"], "SENT")

    r = client.delete("/users/me", headers=headers)
    assert r.status_code == 409, r.text
    assert _user_row(uid).email == email


def test_delete_me_succeeds_with_only_finished_orders(client: TestClient, register_and_login, uniq: str):
    email = f"del_finished_{uniq}@example.com"
    headers = register_and_login(email)
    admin_headers = register_and_login(f"del_admin4_{uniq}@example.com", role="admin")
    uid = _get_user_id(client, admin_headers, email)

    cmd = _make_commande(client, headers, uniq)
    _set_status(client, admin_headers, cmd["id_commande"], "FINISHED")

    r = client.delete("/users/me", headers=headers)
    assert r.status_code == 204, r.text

    row = _user_row(uid)
    assert row.email == f"deleted-{uid}@anonymized.invalid"

    # The order history stays attached to the (now anonymized) user row.
    db = SessionLocal()
    try:
        kept = (
            db.query(models.Commande)
            .filter(models.Commande.id_commande == cmd["id_commande"])
            .first()
        )
        assert kept is not None
        assert int(kept.id_utilisateur) == uid
    finally:
        db.close()


def test_delete_me_succeeds_with_cancelled_or_refunded_orders(client: TestClient, register_and_login, uniq: str):
    email = f"del_cancelled_{uniq}@example.com"
    headers = register_and_login(email)

    cmd = _make_commande(client, headers, uniq)
    r = client.post(f"/orders/commandes/{cmd['id_commande']}/cancel", headers=headers)
    assert r.status_code == 200, r.text

    r = client.delete("/users/me", headers=headers)
    assert r.status_code == 204, r.text


def test_admin_delete_refused_with_open_order(client: TestClient, register_and_login, uniq: str):
    email = f"del_admintarget1_{uniq}@example.com"
    headers = register_and_login(email)
    admin_headers = register_and_login(f"del_admin6_{uniq}@example.com", role="admin")
    uid = _get_user_id(client, admin_headers, email)

    _make_commande(client, headers, uniq)

    r = client.delete(f"/users/{uid}", headers=admin_headers)
    assert r.status_code == 409, r.text
    assert _user_row(uid).email == email


def test_admin_delete_anonymizes_instead_of_hard_deleting(client: TestClient, register_and_login, uniq: str):
    """Regression test: the admin delete endpoint used to call a generic hard
    delete. Since commande.id_utilisateur is ON DELETE RESTRICT, deleting a
    user with any order on record (even a finished one) used to blow up with
    an unhandled DB error instead of anonymizing like DELETE /users/me does."""
    email = f"del_admintarget2_{uniq}@example.com"
    headers = register_and_login(email)
    admin_headers = register_and_login(f"del_admin7_{uniq}@example.com", role="admin")
    uid = _get_user_id(client, admin_headers, email)

    cmd = _make_commande(client, headers, uniq)
    _set_status(client, admin_headers, cmd["id_commande"], "FINISHED")

    r = client.delete(f"/users/{uid}", headers=admin_headers)
    assert r.status_code == 204, r.text

    row = _user_row(uid)
    assert row is not None  # anonymized, not hard-deleted
    assert row.email == f"deleted-{uid}@anonymized.invalid"


def test_admin_delete_succeeds_with_no_orders(client: TestClient, register_and_login, uniq: str):
    email = f"del_admintarget3_{uniq}@example.com"
    register_and_login(email)
    admin_headers = register_and_login(f"del_admin8_{uniq}@example.com", role="admin")
    uid = _get_user_id(client, admin_headers, email)

    r = client.delete(f"/users/{uid}", headers=admin_headers)
    assert r.status_code == 204, r.text
    assert _user_row(uid).email == f"deleted-{uid}@anonymized.invalid"
