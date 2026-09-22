from __future__ import annotations

from fastapi import APIRouter, HTTPException

from infrastructure import models
from presentation.deps import AdminUser, DbSession
from presentation.schemas import (
    AdminCommandeStatusUpdate,
    CommandeAdminRead,
    CommandeRead,
    LigneCommandeAdminRead,
    LigneCommandeRead,
)
from services.order_service import (
    ALL_STATUSES,
    OPEN_STATUSES,
    PAID_NOT_ADVANCED_STATUSES,
    PAID_STATUSES,
    TERMINAL_STATUSES,
    cancel_commande,
    finalize_commande,
    refund_commande,
)

router = APIRouter(prefix="/orders/admin", tags=["orders-admin"])


def _build_commande_admin_read(obj: models.Commande) -> CommandeAdminRead:
    u = obj.utilisateur
    adresse = None
    if u and (u.billing_address_line1 or u.billing_city):
        parts = [u.billing_address_line1, f"{u.billing_postal_code or ''} {u.billing_city or ''}".strip()]
        adresse = ", ".join(p for p in parts if p)
    return CommandeAdminRead(
        **CommandeRead.model_validate(obj).model_dump(),
        client_nom=u.nom if u else None,
        client_prenom=u.prenom if u else None,
        client_email=u.email if u else None,
        client_adresse=adresse,
    )


@router.get("/commandes", response_model=list[CommandeAdminRead])
def admin_list_commandes(db: DbSession, _admin: AdminUser):
    commandes = db.query(models.Commande).order_by(models.Commande.date_commande.desc()).all()
    return [_build_commande_admin_read(c) for c in commandes]


@router.get("/commandes/{id_commande}/lignes", response_model=list[LigneCommandeAdminRead])
def admin_get_lignes(id_commande: int, db: DbSession, _admin: AdminUser):
    lignes = db.query(models.LigneCommande).filter(models.LigneCommande.id_commande == id_commande).all()
    return [
        LigneCommandeAdminRead(
            **LigneCommandeRead.model_validate(ligne).model_dump(),
            titre_livre=ligne.livre.titre if ligne.livre else None,
            sku_livre=ligne.livre.sku if ligne.livre else None,
        )
        for ligne in lignes
    ]


@router.put("/commandes/{id_commande}/status", response_model=CommandeRead)
def admin_set_status(id_commande: int, payload: AdminCommandeStatusUpdate, db: DbSession, _admin: AdminUser):
    obj = db.query(models.Commande).filter(models.Commande.id_commande == id_commande).first()
    if obj is None:
        raise HTTPException(status_code=404, detail="Commande introuvable.")
    new_status = payload.statut.upper()
    if new_status not in ALL_STATUSES:
        raise HTTPException(status_code=400, detail=f"Statut inconnu : {payload.statut}")
    cur = (obj.statut or "").upper()
    # Route the two stock-affecting transitions through the same helpers the
    # normal flow uses, instead of only writing the status column. Setting an
    # unpaid order to PAID by hand used to leave its cart reservation in place
    # forever (quantite_reservee never cleared, quantite_disponible never
    # decremented), so the books stayed invisible in the catalogue; setting it
    # to CANCELLED leaked the reservation the same way.
    if cur in OPEN_STATUSES and new_status in PAID_STATUSES:
        finalize_commande(db, int(obj.id_commande))  # type: ignore[arg-type]
        db.commit()
        db.refresh(obj)
        if new_status != "PAID":
            obj.statut = new_status  # type: ignore[assignment]
            db.commit()
            db.refresh(obj)
        return obj
    if cur in OPEN_STATUSES and new_status in TERMINAL_STATUSES:
        cancel_commande(db, obj)
        obj.statut = new_status  # type: ignore[assignment]
        db.commit()
        db.refresh(obj)
        return obj
    obj.statut = new_status  # type: ignore[assignment]
    db.commit()
    db.refresh(obj)
    return obj


@router.post("/commandes/{id_commande}/advance", response_model=CommandeRead)
def admin_advance(id_commande: int, db: DbSession, _admin: AdminUser):
    obj = db.query(models.Commande).filter(models.Commande.id_commande == id_commande).first()
    if obj is None:
        raise HTTPException(status_code=404, detail="Commande introuvable.")
    # Simple state machine for order progression
    cur = (obj.statut or "").upper()
    sm = (obj.shipping_method or "POST").upper()
    if cur in OPEN_STATUSES:
        # finalize_commande turns the cart reservation into an actual stock
        # decrement and sets statut = "PAID" itself. Writing "PAID" directly
        # here (the old behaviour) skipped that, so the reserved units were
        # never consumed nor released and the book stayed out of the catalogue.
        finalize_commande(db, int(obj.id_commande))  # type: ignore[arg-type]
        db.commit()
        db.refresh(obj)
        return obj
    elif cur == "PAID":
        if sm == "CLICK_COLLECT":
            obj.statut = "AT_RECEPTION"
        else:
            obj.statut = "SENT"
    elif cur == "AT_RECEPTION":
        obj.statut = "FINISHED"
    elif cur == "SENT":
        obj.statut = "FINISHED"
    else:
        # leave unchanged
        pass
    db.commit()
    db.refresh(obj)
    return obj


@router.post("/commandes/{id_commande}/cancel", response_model=CommandeAdminRead)
def admin_cancel_commande(id_commande: int, db: DbSession, _admin: AdminUser):
    obj = db.query(models.Commande).filter(models.Commande.id_commande == id_commande).first()
    if obj is None:
        raise HTTPException(status_code=404, detail="Commande introuvable.")
    cancel_commande(db, obj)
    db.commit()
    db.refresh(obj)
    return _build_commande_admin_read(obj)


@router.post("/commandes/{id_commande}/refund", response_model=CommandeAdminRead)
def admin_refund_commande(id_commande: int, db: DbSession, _admin: AdminUser):
    """Admin-only refund: restores sold stock and marks the order/payments REFUNDED.

    Refunds are an admin/back-office action coordinated with the payment
    provider, not customer self-service — see order_router.py's PaiementUpdate
    handling for why the client can no longer trigger this directly.
    """
    obj = db.query(models.Commande).filter(models.Commande.id_commande == id_commande).first()
    if obj is None:
        raise HTTPException(status_code=404, detail="Commande introuvable.")
    cur = (obj.statut or "").upper()
    if cur not in PAID_STATUSES:
        raise HTTPException(status_code=400, detail=f"Remboursement impossible depuis le statut {cur}.")
    refund_commande(db, id_commande)
    obj.statut = "REFUNDED"  # type: ignore[assignment]
    db.query(models.Paiement).filter(models.Paiement.id_commande == id_commande).update({"statut": "REFUNDED"})
    db.commit()
    db.refresh(obj)
    return _build_commande_admin_read(obj)


@router.post("/commandes/{id_commande}/sent", response_model=CommandeAdminRead)
def admin_set_sent(id_commande: int, db: DbSession, _admin: AdminUser):
    obj = db.query(models.Commande).filter(models.Commande.id_commande == id_commande).first()
    if obj is None:
        raise HTTPException(status_code=404, detail="Commande introuvable.")
    cur = (obj.statut or "").upper()
    if cur not in PAID_NOT_ADVANCED_STATUSES:
        raise HTTPException(status_code=400, detail=f"Passage à « Expédiée » impossible depuis le statut {cur}.")
    obj.statut = "SENT"  # type: ignore[assignment]
    db.commit()
    db.refresh(obj)
    return _build_commande_admin_read(obj)


@router.post("/commandes/{id_commande}/at-reception", response_model=CommandeAdminRead)
def admin_set_at_reception(id_commande: int, db: DbSession, _admin: AdminUser):
    obj = db.query(models.Commande).filter(models.Commande.id_commande == id_commande).first()
    if obj is None:
        raise HTTPException(status_code=404, detail="Commande introuvable.")
    cur = (obj.statut or "").upper()
    if cur not in PAID_NOT_ADVANCED_STATUSES:
        raise HTTPException(status_code=400, detail=f"Passage à « En réception » impossible depuis le statut {cur}.")
    obj.statut = "AT_RECEPTION"  # type: ignore[assignment]
    db.commit()
    db.refresh(obj)
    return _build_commande_admin_read(obj)
