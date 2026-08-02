from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text

from infrastructure import models
from infrastructure.crud_base import CrudBase
from presentation.deps import get_current_user, get_db
from presentation.schemas import (
    CommandeCreate,
    CommandeRead,
    CommandeUpdate,
    LigneCommandeCreate,
    LigneCommandeRead,
    LigneCommandeUpdate,
)
from services.order_service import (
    SHIPPING_FEES_CHF,
    attach_seconds_left,
    cancel_commande,
    cleanup_expired_carts,
    ensure_commande_mutable,
    generate_numero_commande,
    get_commande_owned,
    recompute_commande_total,
    release_ligne_reservation,
    release_stock,
    reserve_stock,
)

router = APIRouter(prefix="/orders", tags=["orders"])

commande_crud = CrudBase[models.Commande](models.Commande, "id_commande")


@router.get("/commandes", response_model=list[CommandeRead])
def list_commandes(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return db.query(models.Commande).filter(models.Commande.id_utilisateur == current_user.id_utilisateur).all()


@router.get("/commandes/{id_commande}", response_model=CommandeRead)
def get_commande(id_commande: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    cleanup_expired_carts(db)
    obj = get_commande_owned(db, id_commande, int(current_user.id_utilisateur))
    if obj is None:
        raise HTTPException(status_code=404, detail="Commande not found")
    return attach_seconds_left(db, obj)


@router.post("/commandes", response_model=CommandeRead, status_code=status.HTTP_201_CREATED)
def create_commande(payload: CommandeCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    cleanup_expired_carts(db)
    shipping_method = (payload.shipping_method or "POST").upper()
    if shipping_method not in SHIPPING_FEES_CHF:
        raise HTTPException(status_code=400, detail="Invalid shipping method")
    obj = models.Commande(
        id_utilisateur=current_user.id_utilisateur,
        numero_commande=generate_numero_commande(db),
        shipping_method=shipping_method,
        frais_port_chf=SHIPPING_FEES_CHF[shipping_method],
        montant_total_chf=0,
        statut="CREATED",
    )
    created = commande_crud.create(db, obj)
    # Set expiry with the DB clock so it is always exactly 20 minutes AFTER
    # creation (avoids timezone drift between MySQL NOW() and Python UTC, which
    # previously could place the expiry before the creation timestamp).
    db.execute(
        text("UPDATE commande SET cart_expires_at = (NOW() + INTERVAL 20 MINUTE) WHERE id_commande = :id"),
        {"id": int(created.id_commande)},
    )
    db.commit()
    db.refresh(created)
    return attach_seconds_left(db, created)


@router.put("/commandes/{id_commande}", response_model=CommandeRead)
def update_commande(
    id_commande: int,
    payload: CommandeUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    obj = get_commande_owned(db, id_commande, int(current_user.id_utilisateur))
    if obj is None:
        raise HTTPException(status_code=404, detail="Commande not found")
    ensure_commande_mutable(obj)
    data = payload.model_dump(exclude_unset=True)
    shipping_method = data.pop("shipping_method", None)
    if shipping_method is not None:
        shipping_method = shipping_method.upper()
        if shipping_method not in SHIPPING_FEES_CHF:
            raise HTTPException(status_code=400, detail="Invalid shipping method")
        obj.shipping_method = shipping_method  # type: ignore[assignment]
        obj.frais_port_chf = SHIPPING_FEES_CHF[shipping_method]  # type: ignore[assignment]
    for k, v in data.items():
        if hasattr(obj, k):
            setattr(obj, k, v)
    recompute_commande_total(db, obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.post("/commandes/{id_commande}/cancel", response_model=CommandeRead)
def cancel_own_commande(id_commande: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """Customer-facing cancel: releases the cart reservation immediately instead
    of leaving stock reserved for the full 20-minute cart_expires_at window."""
    obj = get_commande_owned(db, id_commande, int(current_user.id_utilisateur))
    if obj is None:
        raise HTTPException(status_code=404, detail="Commande not found")
    cancel_commande(db, obj)
    db.commit()
    db.refresh(obj)
    return attach_seconds_left(db, obj)


@router.delete("/commandes/{id_commande}", status_code=status.HTTP_204_NO_CONTENT)
def delete_commande(id_commande: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    obj = get_commande_owned(db, id_commande, int(current_user.id_utilisateur))
    if obj is None:
        raise HTTPException(status_code=404, detail="Commande not found")
    cur = (obj.statut or "").upper()
    if cur in ("CREATED", "PENDING"):
        # Release any reserved stock before deleting — otherwise the cascade
        # delete of the lignes silently leaks the reservation forever.
        lignes = db.query(models.LigneCommande).filter(models.LigneCommande.id_commande == id_commande).all()
        for l in lignes:
            release_ligne_reservation(db, l)
    db.delete(obj)
    db.commit()
    return None


@router.get("/lignes", response_model=list[LigneCommandeRead])
def list_lignes(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return (
        db.query(models.LigneCommande)
        .join(models.Commande, models.LigneCommande.id_commande == models.Commande.id_commande)
        .filter(models.Commande.id_utilisateur == current_user.id_utilisateur)
        .all()
    )


@router.get("/lignes/{id_ligne_commande}", response_model=LigneCommandeRead)
def get_ligne(id_ligne_commande: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    obj = (
        db.query(models.LigneCommande)
        .join(models.Commande, models.LigneCommande.id_commande == models.Commande.id_commande)
        .filter(
            models.LigneCommande.id_ligne_commande == id_ligne_commande,
            models.Commande.id_utilisateur == current_user.id_utilisateur,
        )
        .first()
    )
    if obj is None:
        raise HTTPException(status_code=404, detail="LigneCommande not found")
    return obj


@router.post("/lignes", response_model=LigneCommandeRead, status_code=status.HTTP_201_CREATED)
def create_ligne(payload: LigneCommandeCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    cleanup_expired_carts(db)
    c = get_commande_owned(db, payload.id_commande, int(current_user.id_utilisateur))
    if c is None:
        raise HTTPException(status_code=404, detail="Commande not found")
    if (c.statut or "").upper() in ("CANCELLED", "FAILED"):
        raise HTTPException(status_code=409, detail="Votre réservation a expiré. Retournez au panier.")
    ensure_commande_mutable(c)
    article = db.query(models.Article).filter(models.Article.id_article == payload.id_article).first()
    if article is None:
        raise HTTPException(status_code=404, detail="Article not found")
    # Unit price always comes from the catalog, never the client — otherwise a
    # tampered request body could set an arbitrary prix_unitaire_chf.
    unit_price = float(article.prix_chf)  # type: ignore[arg-type]
    try:
        reserve_stock(db, int(payload.id_article), int(payload.quantite))

        # create the ligne and commit once (for articles without stock rows, we allow creation)
        obj = models.LigneCommande(
            id_commande=payload.id_commande,
            id_article=payload.id_article,
            quantite=payload.quantite,
            prix_unitaire_chf=unit_price,
        )
        db.add(obj)

        # NOTE: we intentionally do NOT set article.actif = False here.
        # Reserving stock for a cart (which may be abandoned) must not delist the
        # book from the catalogue. The article is only marked inactive when the
        # order is actually paid (see finalize_commande). Over-reservation is
        # still prevented by the "Not enough stock" check above.

        db.flush()
        recompute_commande_total(db, c)
        db.commit()
        db.refresh(obj)
        return obj
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Could not create ligne: {e}") from e


@router.put("/lignes/{id_ligne_commande}", response_model=LigneCommandeRead)
def update_ligne(
    id_ligne_commande: int,
    payload: LigneCommandeUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    obj = (
        db.query(models.LigneCommande)
        .join(models.Commande, models.LigneCommande.id_commande == models.Commande.id_commande)
        .filter(
            models.LigneCommande.id_ligne_commande == id_ligne_commande,
            models.Commande.id_utilisateur == current_user.id_utilisateur,
        )
        .first()
    )
    if obj is None:
        raise HTTPException(status_code=404, detail="LigneCommande not found")
    parent = db.query(models.Commande).filter(models.Commande.id_commande == obj.id_commande).first()
    if parent is not None:
        ensure_commande_mutable(parent)
    data = payload.model_dump(exclude_unset=True)
    new_qty = data.get("quantite")
    try:
        if new_qty is not None and int(new_qty) != int(obj.quantite):  # type: ignore[arg-type]
            delta = int(new_qty) - int(obj.quantite)  # type: ignore[arg-type]
            if delta > 0:
                reserve_stock(db, int(obj.id_article), delta)  # type: ignore[arg-type]
            else:
                release_stock(db, int(obj.id_article), -delta)  # type: ignore[arg-type]
            obj.quantite = int(new_qty)  # type: ignore[assignment]

        db.flush()
        commande = db.query(models.Commande).filter(models.Commande.id_commande == obj.id_commande).first()
        if commande is not None:
            recompute_commande_total(db, commande)
        db.commit()
        db.refresh(obj)
        return obj
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Could not update ligne: {e}") from e


@router.delete("/lignes/{id_ligne_commande}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ligne(id_ligne_commande: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    obj = (
        db.query(models.LigneCommande)
        .join(models.Commande, models.LigneCommande.id_commande == models.Commande.id_commande)
        .filter(
            models.LigneCommande.id_ligne_commande == id_ligne_commande,
            models.Commande.id_utilisateur == current_user.id_utilisateur,
        )
        .first()
    )
    if obj is None:
        raise HTTPException(status_code=404, detail="LigneCommande not found")
    ensure_commande_mutable(obj.commande)  # type: ignore[attr-defined]
    id_commande = int(obj.id_commande)  # type: ignore[arg-type]
    if (obj.commande.statut or "").upper() in ("CREATED", "PENDING"):  # type: ignore[attr-defined]
        # Release the reservation before deleting — otherwise it leaks forever.
        release_ligne_reservation(db, obj)
    db.delete(obj)
    db.flush()
    commande = db.query(models.Commande).filter(models.Commande.id_commande == id_commande).first()
    if commande is not None:
        recompute_commande_total(db, commande)
    db.commit()
    return None
