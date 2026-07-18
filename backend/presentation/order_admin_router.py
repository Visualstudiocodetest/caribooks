from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from infrastructure import models
from presentation.deps import get_db, require_admin
from presentation.schemas import (
    AdminCommandeStatusUpdate,
    CommandeAdminRead,
    CommandeRead,
    LigneCommandeAdminRead,
    LigneCommandeRead,
)
from services.order_service import cancel_commande, refund_commande

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
def admin_list_commandes(db: Session = Depends(get_db), _admin=Depends(require_admin)):
    commandes = db.query(models.Commande).order_by(models.Commande.date_commande.desc()).all()
    return [_build_commande_admin_read(c) for c in commandes]


@router.get("/commandes/{id_commande}/lignes", response_model=list[LigneCommandeAdminRead])
def admin_get_lignes(id_commande: int, db: Session = Depends(get_db), _admin=Depends(require_admin)):
    lignes = db.query(models.LigneCommande).filter(models.LigneCommande.id_commande == id_commande).all()
    return [
        LigneCommandeAdminRead(
            **LigneCommandeRead.model_validate(l).model_dump(),
            titre_article=l.article.titre if l.article else None,
            sku_article=l.article.sku if l.article else None,
        )
        for l in lignes
    ]


@router.put("/commandes/{id_commande}/status", response_model=CommandeRead)
def admin_set_status(id_commande: int, payload: AdminCommandeStatusUpdate, db: Session = Depends(get_db), _admin=Depends(require_admin)):
    obj = db.query(models.Commande).filter(models.Commande.id_commande == id_commande).first()
    if obj is None:
        raise HTTPException(status_code=404, detail="Commande not found")
    obj.statut = payload.statut  # type: ignore[assignment]
    db.commit()
    db.refresh(obj)
    return obj


@router.post("/commandes/{id_commande}/advance", response_model=CommandeRead)
def admin_advance(id_commande: int, db: Session = Depends(get_db), _admin=Depends(require_admin)):
    obj = db.query(models.Commande).filter(models.Commande.id_commande == id_commande).first()
    if obj is None:
        raise HTTPException(status_code=404, detail="Commande not found")
    # Simple state machine for order progression
    cur = (obj.statut or "").upper()
    sm = (obj.shipping_method or "POST").upper()
    if cur in ("CREATED", "PENDING"):
        obj.statut = "PAID"
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
def admin_cancel_commande(id_commande: int, db: Session = Depends(get_db), _admin=Depends(require_admin)):
    obj = db.query(models.Commande).filter(models.Commande.id_commande == id_commande).first()
    if obj is None:
        raise HTTPException(status_code=404, detail="Commande not found")
    cancel_commande(db, obj)
    db.commit()
    db.refresh(obj)
    return _build_commande_admin_read(obj)


@router.post("/commandes/{id_commande}/refund", response_model=CommandeAdminRead)
def admin_refund_commande(id_commande: int, db: Session = Depends(get_db), _admin=Depends(require_admin)):
    """Admin-only refund: restores sold stock and marks the order/payments REFUNDED.

    Refunds are an admin/back-office action coordinated with the payment
    provider, not customer self-service — see order_router.py's PaiementUpdate
    handling for why the client can no longer trigger this directly.
    """
    obj = db.query(models.Commande).filter(models.Commande.id_commande == id_commande).first()
    if obj is None:
        raise HTTPException(status_code=404, detail="Commande not found")
    cur = (obj.statut or "").upper()
    if cur not in ("PAID", "CAPTURED", "COMPLETED", "SENT", "AT_RECEPTION", "FINISHED"):
        raise HTTPException(status_code=400, detail=f"Cannot refund from status {cur}")
    refund_commande(db, id_commande)
    obj.statut = "REFUNDED"  # type: ignore[assignment]
    db.query(models.Paiement).filter(models.Paiement.id_commande == id_commande).update({"statut": "REFUNDED"})
    db.commit()
    db.refresh(obj)
    return _build_commande_admin_read(obj)


@router.post("/commandes/{id_commande}/sent", response_model=CommandeAdminRead)
def admin_set_sent(id_commande: int, db: Session = Depends(get_db), _admin=Depends(require_admin)):
    obj = db.query(models.Commande).filter(models.Commande.id_commande == id_commande).first()
    if obj is None:
        raise HTTPException(status_code=404, detail="Commande not found")
    cur = (obj.statut or "").upper()
    if cur not in ("PAID", "CAPTURED", "COMPLETED"):
        raise HTTPException(status_code=400, detail=f"Cannot mark SENT from status {cur}")
    obj.statut = "SENT"  # type: ignore[assignment]
    db.commit()
    db.refresh(obj)
    return _build_commande_admin_read(obj)


@router.post("/commandes/{id_commande}/at-reception", response_model=CommandeAdminRead)
def admin_set_at_reception(id_commande: int, db: Session = Depends(get_db), _admin=Depends(require_admin)):
    obj = db.query(models.Commande).filter(models.Commande.id_commande == id_commande).first()
    if obj is None:
        raise HTTPException(status_code=404, detail="Commande not found")
    cur = (obj.statut or "").upper()
    if cur not in ("PAID", "CAPTURED", "COMPLETED"):
        raise HTTPException(status_code=400, detail=f"Cannot mark AT_RECEPTION from status {cur}")
    obj.statut = "AT_RECEPTION"  # type: ignore[assignment]
    db.commit()
    db.refresh(obj)
    return _build_commande_admin_read(obj)
