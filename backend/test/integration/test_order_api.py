from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient


def _make_article(client: TestClient, admin_headers: dict, uniq: str, prix_chf: float = 20.0) -> int:
    r = client.post(
        "/catalog/type-objets",
        json={"libelle": "Livre", "code": f"ORDBOOK_{uniq}", "description": "d"},
        headers=admin_headers,
    )
    assert r.status_code == 201, r.text
    type_id = r.json()["id_type_objet"]
    r = client.post("/catalog/etat-usures", json={"libelle": f"EtatOrd_{uniq}", "description": "d"}, headers=admin_headers)
    assert r.status_code == 201, r.text
    etat_id = r.json()["id_etat_usure"]
    r = client.post(
        "/articles/",
        json={
            "id_type_objet": type_id,
            "id_etat_usure": etat_id,
            "sku": f"SKU_ORD_{uniq}",
            "titre": "Order article",
            "prix_chf": prix_chf,
            "actif": True,
            "categorie_ids": [],
        },
        headers=admin_headers,
    )
    assert r.status_code == 201, r.text
    return r.json()["id_article"]


def _make_stock(client: TestClient, admin_headers: dict, uniq: str, article_id: int, qty: int = 10) -> None:
    r = client.post(
        "/stock/sources",
        json={"libelle": f"SourceOrd_{uniq}", "type_source": "WAREHOUSE", "description": "d"},
        headers=admin_headers,
    )
    assert r.status_code == 201, r.text
    source_id = r.json()["id_source_stock"]
    r = client.post(
        "/stock/",
        json={
            "id_article": article_id,
            "id_source_stock": source_id,
            "quantite_disponible": qty,
            "quantite_reservee": 0,
        },
        headers=admin_headers,
    )
    assert r.status_code == 201, r.text


def test_orders_lignes_paiements_scoped_to_user(client: TestClient, register_and_login, uniq: str):
    headers = register_and_login(f"orders_{uniq}@example.com")
    admin_headers = register_and_login(f"orders_admin_{uniq}@example.com", role="admin")

    article_id = _make_article(client, admin_headers, uniq, prix_chf=20.0)
    _make_stock(client, admin_headers, uniq, article_id, qty=10)

    # Commande: server derives statut/frais_port_chf/montant_total_chf, never the client.
    r = client.post(
        "/orders/commandes",
        json={"numero_commande": f"CMD_{uniq}", "shipping_method": "POST"},
        headers=headers,
    )
    assert r.status_code == 201, r.text
    cmd = r.json()
    assert cmd["statut"] == "CREATED"
    assert cmd["montant_total_chf"] == 0
    assert cmd["frais_port_chf"] == 9.0

    assert client.get("/orders/commandes", headers=headers).status_code == 200
    assert client.get(f"/orders/commandes/{cmd['id_commande']}", headers=headers).status_code == 200

    # LigneCommande: unit price always comes from the catalog (Article.prix_chf).
    r = client.post(
        "/orders/lignes",
        json={"id_commande": cmd["id_commande"], "id_article": article_id, "quantite": 2},
        headers=headers,
    )
    assert r.status_code == 201, r.text
    ligne = r.json()
    assert ligne["prix_unitaire_chf"] == 20.0
    assert client.get("/orders/lignes", headers=headers).status_code == 200
    assert client.get(f"/orders/lignes/{ligne['id_ligne_commande']}", headers=headers).status_code == 200

    # Total recomputed server-side: 2 * 20.0 + 9.0 shipping = 49.0
    r = client.get(f"/orders/commandes/{cmd['id_commande']}", headers=headers)
    assert r.json()["montant_total_chf"] == 49.0

    r = client.put(
        f"/orders/lignes/{ligne['id_ligne_commande']}",
        json={"quantite": 3},
        headers=headers,
    )
    assert r.status_code == 200
    assert r.json()["quantite"] == 3
    r = client.get(f"/orders/commandes/{cmd['id_commande']}", headers=headers)
    assert r.json()["montant_total_chf"] == 69.0  # 3 * 20.0 + 9.0

    # Paiement: created PENDING regardless of client-submitted fields (see below test).
    r = client.post(
        "/orders/paiements",
        json={
            "id_commande": cmd["id_commande"],
            "reference_externe": f"REF_{uniq}",
            "devise": "CHF",
            "fournisseur_paiement": "POSTFINANCE",
        },
        headers=headers,
    )
    assert r.status_code == 201, r.text
    pay = r.json()
    assert pay["statut"] == "PENDING"
    assert pay["montant_chf"] == 69.0
    assert client.get("/orders/paiements", headers=headers).status_code == 200
    assert client.get(f"/orders/paiements/{pay['id_paiement']}", headers=headers).status_code == 200

    # cleanup
    assert client.delete(f"/orders/paiements/{pay['id_paiement']}", headers=headers).status_code == 204
    assert client.delete(f"/orders/lignes/{ligne['id_ligne_commande']}", headers=headers).status_code == 204
    assert client.delete(f"/orders/commandes/{cmd['id_commande']}", headers=headers).status_code == 204


def test_ligne_price_tampering_is_ignored(client: TestClient, register_and_login, uniq: str):
    """A tampered prix_unitaire_chf in the request body must never override the
    catalog price — this was the free-order vector fixed alongside the
    payment-status bypass."""
    headers = register_and_login(f"orders_tamper_{uniq}@example.com")
    admin_headers = register_and_login(f"orders_tamper_admin_{uniq}@example.com", role="admin")
    article_id = _make_article(client, admin_headers, uniq, prix_chf=50.0)

    r = client.post(
        "/orders/commandes",
        json={"numero_commande": f"CMD_TAMPER_{uniq}"},
        headers=headers,
    )
    cmd = r.json()

    r = client.post(
        "/orders/lignes",
        json={
            "id_commande": cmd["id_commande"],
            "id_article": article_id,
            "quantite": 1,
            "prix_unitaire_chf": 0.01,  # tampered — schema no longer declares this field
        },
        headers=headers,
    )
    assert r.status_code == 201, r.text
    assert r.json()["prix_unitaire_chf"] == 50.0


def test_commande_shipping_fee_tampering_is_ignored(client: TestClient, register_and_login, uniq: str):
    headers = register_and_login(f"orders_shipfee_{uniq}@example.com")
    r = client.post(
        "/orders/commandes",
        json={"numero_commande": f"CMD_SHIP_{uniq}", "shipping_method": "POST", "frais_port_chf": 0.01},
        headers=headers,
    )
    assert r.status_code == 201, r.text
    assert r.json()["frais_port_chf"] == 9.0

    r = client.post(
        "/orders/commandes",
        json={"numero_commande": f"CMD_SHIP2_{uniq}", "shipping_method": "CLICK_COLLECT"},
        headers=headers,
    )
    assert r.status_code == 201, r.text
    assert r.json()["frais_port_chf"] == 1.0

    r = client.post(
        "/orders/commandes",
        json={"numero_commande": f"CMD_SHIP3_{uniq}", "shipping_method": "TELEPORT"},
        headers=headers,
    )
    assert r.status_code == 400


def test_paiement_status_and_amount_not_client_settable(client: TestClient, register_and_login, uniq: str):
    """The core payment-bypass fix: a client can no longer forge a CAPTURED/PAID
    status (or an arbitrary amount) at payment creation or update time. Only a
    verified PostFinance/Payrexx callback may transition a payment's status."""
    headers = register_and_login(f"orders_bypass_{uniq}@example.com")
    admin_headers = register_and_login(f"orders_bypass_admin_{uniq}@example.com", role="admin")
    article_id = _make_article(client, admin_headers, uniq, prix_chf=100.0)
    _make_stock(client, admin_headers, uniq, article_id, qty=5)

    r = client.post("/orders/commandes", json={"numero_commande": f"CMD_BYP_{uniq}"}, headers=headers)
    cmd = r.json()
    client.post(
        "/orders/lignes",
        json={"id_commande": cmd["id_commande"], "id_article": article_id, "quantite": 1},
        headers=headers,
    )

    r = client.post(
        "/orders/paiements",
        json={
            "id_commande": cmd["id_commande"],
            "reference_externe": f"REF_BYP_{uniq}",
            "montant_chf": 0.01,
            "statut": "CAPTURED",
        },
        headers=headers,
    )
    assert r.status_code == 201, r.text
    pay = r.json()
    assert pay["statut"] == "PENDING"
    assert pay["montant_chf"] == 109.0  # 1 * 100.0 + 9.0 default POST shipping

    # the commande must NOT have been finalized by the forged status
    r = client.get(f"/orders/commandes/{cmd['id_commande']}", headers=headers)
    assert r.json()["statut"] == "CREATED"

    # nor can the client flip it to CAPTURED via the update route
    r = client.put(
        f"/orders/paiements/{pay['id_paiement']}",
        json={"statut": "CAPTURED"},
        headers=headers,
    )
    assert r.status_code == 200
    assert r.json()["statut"] == "PENDING"


def test_local_webhook_finalizes_and_is_idempotent(client: TestClient, register_and_login, uniq: str):
    """The local dev webhook (the only way to reach _finalize_commande without
    real PostFinance credentials) must both finalize on first delivery and be
    idempotent on replay — a retried webhook must not double-decrement stock."""
    headers = register_and_login(f"orders_webhook_{uniq}@example.com")
    admin_headers = register_and_login(f"orders_webhook_admin_{uniq}@example.com", role="admin")
    article_id = _make_article(client, admin_headers, uniq, prix_chf=10.0)
    _make_stock(client, admin_headers, uniq, article_id, qty=5)

    r = client.post("/orders/commandes", json={"numero_commande": f"CMD_WH_{uniq}"}, headers=headers)
    cmd = r.json()
    r = client.post(
        "/orders/lignes",
        json={"id_commande": cmd["id_commande"], "id_article": article_id, "quantite": 2},
        headers=headers,
    )
    assert r.status_code == 201, r.text

    r = client.post(
        "/orders/paiements",
        json={"id_commande": cmd["id_commande"], "reference_externe": f"REF_WH_{uniq}"},
        headers=headers,
    )
    pay = r.json()

    stock_before = client.get("/stock/", headers=admin_headers).json()
    row_before = next(s for s in stock_before if s["id_article"] == article_id)
    assert row_before["quantite_disponible"] == 5
    assert row_before["quantite_reservee"] == 2  # reserved by create_ligne

    webhook_payload = {"reference": f"REF_WH_{uniq}", "status": "AUTHORIZED"}
    r = client.post("/orders/paiements/webhook/local", json=webhook_payload)
    assert r.status_code == 200, r.text

    # Finalizing a fully-pre-reserved sale only clears the reservation —
    # quantite_disponible is untouched since the quantity was already reserved.
    stock_after = client.get("/stock/", headers=admin_headers).json()
    row_after = next(s for s in stock_after if s["id_article"] == article_id)
    assert row_after["quantite_disponible"] == 5
    assert row_after["quantite_reservee"] == 0

    # Replay the same webhook. Without the idempotency guard, _finalize_commande
    # would see quantite_reservee already at 0 and wrongly fall through to
    # deducting straight from quantite_disponible a second time.
    r = client.post("/orders/paiements/webhook/local", json=webhook_payload)
    assert r.status_code == 200, r.text
    stock_replay = client.get("/stock/", headers=admin_headers).json()
    row_replay = next(s for s in stock_replay if s["id_article"] == article_id)
    assert row_replay["quantite_disponible"] == 5  # unchanged — proves idempotency
    assert row_replay["quantite_reservee"] == 0


def test_local_webhook_disabled_outside_development(client: TestClient, monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    r = client.post("/orders/paiements/webhook/local", json={"reference": "does-not-matter"})
    assert r.status_code == 404

    monkeypatch.setenv("ENVIRONMENT", "staging")
    r = client.post("/orders/paiements/webhook/local", json={"reference": "does-not-matter"})
    assert r.status_code == 404


def test_postfinance_webhook_requires_valid_signature(client: TestClient, register_and_login, uniq: str):
    r = client.post("/orders/paiements/webhook/postfinance", json={"id": "x"})
    assert r.status_code == 403  # missing signature

    with patch("presentation.order_router.verify_postfinance_webhook_signature", return_value=False):
        r = client.post(
            "/orders/paiements/webhook/postfinance",
            json={"id": "x"},
            headers={"x-signature": "invalid"},
        )
        assert r.status_code == 403


def test_postfinance_webhook_finalizes_and_is_idempotent(client: TestClient, register_and_login, uniq: str):
    headers = register_and_login(f"orders_pfwh_{uniq}@example.com")
    admin_headers = register_and_login(f"orders_pfwh_admin_{uniq}@example.com", role="admin")
    article_id = _make_article(client, admin_headers, uniq, prix_chf=15.0)
    _make_stock(client, admin_headers, uniq, article_id, qty=4)

    r = client.post("/orders/commandes", json={"numero_commande": f"CMD_PFWH_{uniq}"}, headers=headers)
    cmd = r.json()
    client.post(
        "/orders/lignes",
        json={"id_commande": cmd["id_commande"], "id_article": article_id, "quantite": 1},
        headers=headers,
    )
    r = client.post(
        "/orders/paiements",
        json={"id_commande": cmd["id_commande"], "reference_externe": f"REF_PFWH_{uniq}"},
        headers=headers,
    )
    pay_id = r.json()["id_paiement"]

    webhook_body = {"id": f"REF_PFWH_{uniq}", "merchantReference": f"REF_PFWH_{uniq}", "state": "FULFILL"}
    with patch("presentation.order_router.verify_postfinance_webhook_signature", return_value=True):
        r = client.post(
            "/orders/paiements/webhook/postfinance",
            json=webhook_body,
            headers={"x-signature": "sig"},
        )
        assert r.status_code == 200, r.text

        pay_after = client.get(f"/orders/paiements/{pay_id}", headers=headers).json()
        assert pay_after["statut"] == "FULFILL"

        # Finalizing a fully-pre-reserved sale only clears the reservation.
        stock_after = client.get("/stock/", headers=admin_headers).json()
        row = next(s for s in stock_after if s["id_article"] == article_id)
        assert row["quantite_disponible"] == 4
        assert row["quantite_reservee"] == 0

        # Replay — PostFinance explicitly documents webhooks may be delivered
        # more than once. Without the idempotency guard this would wrongly
        # deduct from quantite_disponible a second time (reservee is now 0).
        r = client.post(
            "/orders/paiements/webhook/postfinance",
            json=webhook_body,
            headers={"x-signature": "sig"},
        )
        assert r.status_code == 200, r.text
        stock_replay = client.get("/stock/", headers=admin_headers).json()
        row_replay = next(s for s in stock_replay if s["id_article"] == article_id)
        assert row_replay["quantite_disponible"] == 4


def test_postfinance_iframe_session_and_confirm_local_mode(client: TestClient, register_and_login, uniq: str):
    """The actual frontend-used flow. PostFinance itself is mocked so this test
    is deterministic regardless of whether real sandbox credentials happen to
    be configured in the local/CI environment."""
    headers = register_and_login(f"orders_pfsession_{uniq}@example.com")
    admin_headers = register_and_login(f"orders_pfsession_admin_{uniq}@example.com", role="admin")
    article_id = _make_article(client, admin_headers, uniq, prix_chf=30.0)
    _make_stock(client, admin_headers, uniq, article_id, qty=2)

    r = client.post("/orders/commandes", json={"numero_commande": f"CMD_PFS_{uniq}"}, headers=headers)
    cmd = r.json()
    client.post(
        "/orders/lignes",
        json={"id_commande": cmd["id_commande"], "id_article": article_id, "quantite": 1},
        headers=headers,
    )

    fake_session = {
        "transaction_id": f"local-{uniq}",
        "transaction": {"id": f"local-{uniq}", "state": "PENDING"},
        "payment_methods": [],
        "javascript_url": None,
        "local_mode": True,
        "error": None,
    }
    with patch("presentation.order_router.create_postfinance_iframe_session", return_value=fake_session):
        r = client.post(
            "/orders/paiements/postfinance",
            json={
                "id_commande": cmd["id_commande"],
                "reference_externe": f"REF_PFS_{uniq}",
                "montant_chf": 0.01,  # tampered — ignored, server uses commande total
            },
            headers=headers,
        )
    assert r.status_code == 201, r.text
    session = r.json()
    assert session["local_mode"] is True
    assert session["paiement"]["montant_chf"] == 39.0  # 1 * 30.0 + 9.0 default POST shipping
    pay_id = session["paiement"]["id_paiement"]

    fake_confirm = {"id": f"local-{uniq}", "status": "CONFIRMED", "state": "CONFIRMED", "version": 1, "local": True}
    with patch("presentation.order_router.get_postfinance_transaction", return_value={"version": 1}), \
         patch("presentation.order_router.confirm_postfinance_transaction", return_value=fake_confirm):
        r = client.post(f"/orders/paiements/{pay_id}/confirm-postfinance", headers=headers)
        assert r.status_code == 200, r.text
        assert r.json()["paiement"]["statut"] == "AUTHORIZED"

        stock_after = client.get("/stock/", headers=admin_headers).json()
        row = next(s for s in stock_after if s["id_article"] == article_id)
        assert row["quantite_disponible"] == 2  # unchanged — the reservation is what covered the sale
        assert row["quantite_reservee"] == 0

        # Idempotency: confirming again must not deduct from quantite_disponible
        # now that quantite_reservee is already 0.
        r = client.post(f"/orders/paiements/{pay_id}/confirm-postfinance", headers=headers)
        assert r.status_code == 200, r.text
        stock_replay = client.get("/stock/", headers=admin_headers).json()
        row_replay = next(s for s in stock_replay if s["id_article"] == article_id)
        assert row_replay["quantite_disponible"] == 2
