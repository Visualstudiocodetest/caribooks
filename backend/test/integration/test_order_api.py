from __future__ import annotations

from fastapi.testclient import TestClient
from unittest.mock import patch


def test_orders_lignes_paiements_scoped_to_user(client: TestClient, register_and_login, uniq: str):
    headers = register_and_login(f"orders_{uniq}@example.com")

    # create an article to reference in ligne_commande
    r = client.post(
        "/catalog/type-objets",
        json={"libelle": "Livre", "code": f"ORDBOOK_{uniq}", "description": "d"},
        headers=headers,
    )
    type_id = r.json()["id_type_objet"]
    r = client.post("/catalog/etat-usures", json={"libelle": f"EtatOrd_{uniq}", "description": "d"}, headers=headers)
    etat_id = r.json()["id_etat_usure"]
    r = client.post(
        "/articles/",
        json={
            "id_type_objet": type_id,
            "id_etat_usure": etat_id,
            "sku": f"SKU_ORD_{uniq}",
            "titre": "Order article",
            "prix_chf": 20.0,
            "actif": True,
            "categorie_ids": [],
        },
        headers=headers,
    )
    article_id = r.json()["id_article"]

    # Commande
    r = client.post(
        "/orders/commandes",
        json={"numero_commande": f"CMD_{uniq}", "montant_total_chf": 40.0, "statut": "CREATED"},
        headers=headers,
    )
    assert r.status_code == 201, r.text
    cmd = r.json()

    assert client.get("/orders/commandes", headers=headers).status_code == 200
    assert client.get(f"/orders/commandes/{cmd['id_commande']}", headers=headers).status_code == 200

    r = client.put(
        f"/orders/commandes/{cmd['id_commande']}",
        json={"statut": "PAID"},
        headers=headers,
    )
    assert r.status_code == 200
    assert r.json()["statut"] == "PAID"

    # LigneCommande
    r = client.post(
        "/orders/lignes",
        json={
            "id_commande": cmd["id_commande"],
            "id_article": article_id,
            "quantite": 2,
            "prix_unitaire_chf": 20.0,
        },
        headers=headers,
    )
    assert r.status_code == 201, r.text
    ligne = r.json()
    assert client.get("/orders/lignes", headers=headers).status_code == 200
    assert client.get(f"/orders/lignes/{ligne['id_ligne_commande']}", headers=headers).status_code == 200

    r = client.put(
        f"/orders/lignes/{ligne['id_ligne_commande']}",
        json={"quantite": 3},
        headers=headers,
    )
    assert r.status_code == 200
    assert r.json()["quantite"] == 3

    # Paiement
    r = client.post(
        "/orders/paiements",
        json={
            "id_commande": cmd["id_commande"],
            "reference_externe": f"REF_{uniq}",
            "montant_chf": 60.0,
            "devise": "CHF",
            "statut": "CAPTURED",
            "fournisseur_paiement": "POSTFINANCE",
        },
        headers=headers,
    )
    assert r.status_code == 201, r.text
    pay = r.json()
    assert client.get("/orders/paiements", headers=headers).status_code == 200
    assert client.get(f"/orders/paiements/{pay['id_paiement']}", headers=headers).status_code == 200

    r = client.put(
        f"/orders/paiements/{pay['id_paiement']}",
        json={"statut": "REFUNDED"},
        headers=headers,
    )
    assert r.status_code == 200
    assert r.json()["statut"] == "REFUNDED"

    # cleanup
    assert client.delete(f"/orders/paiements/{pay['id_paiement']}", headers=headers).status_code == 204
    assert client.delete(f"/orders/lignes/{ligne['id_ligne_commande']}", headers=headers).status_code == 204
    assert client.delete(f"/orders/commandes/{cmd['id_commande']}", headers=headers).status_code == 204


@patch("presentation.order_router.create_postfinance_checkout")
@patch("presentation.order_router.get_postfinance_checkout_status")
def test_postfinance_checkout_flow(mock_get_status, mock_create, client: TestClient, register_and_login, uniq: str):
    headers = register_and_login(f"pf_{uniq}@example.com")

    # Create Commande
    r = client.post(
        "/orders/commandes",
        json={"numero_commande": f"CMD_PF_{uniq}", "montant_total_chf": 100.0, "statut": "CREATED"},
        headers=headers,
    )
    cmd = r.json()
    cmd_id = cmd["id_commande"]

    # Mock postfinance creation
    mock_create.return_value = {
        "id": f"pf_{uniq}",
        "status": "CREATED",
        "redirect_url": "https://pay.example.com",
        "raw": {"test": True}
    }

    # Create paiement postfinance
    r = client.post(
        "/orders/paiements/postfinance",
        json={
            "id_commande": cmd_id,
            "montant_chf": 100.0,
            "devise": "CHF",
            "reference_externe": f"pf_{uniq}",
            "statut": "PENDING"
        },
        headers=headers,
    )
    assert r.status_code == 201, r.text
    pay = r.json()["paiement"]
    
    assert pay["fournisseur_paiement"] == "POSTFINANCE"
    assert pay["statut"] == "CREATED"
    assert pay["reference_externe"] == f"pf_{uniq}"
    
    # Mock polling status update
    mock_get_status.return_value = {
        "id": f"pf_{uniq}",
        "status": "COMPLETED",
        "raw": {"test": True}
    }
    
    # Poll
    r = client.get(f"/orders/paiements/{pay['id_paiement']}/poll-postfinance", headers=headers)
    assert r.status_code == 200
    
    updated_pay = r.json()["paiement"]
    assert updated_pay["statut"] == "COMPLETED"
    
    # Cleanup
    assert client.delete(f"/orders/paiements/{pay['id_paiement']}", headers=headers).status_code == 204
    assert client.delete(f"/orders/commandes/{cmd_id}", headers=headers).status_code == 204
