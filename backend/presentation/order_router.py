from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import text

from infrastructure import models
from infrastructure.crud_base import CrudBase
from presentation.deps import CurrentUser, DbSession
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
    cancel_other_open_commandes,
    cleanup_expired_carts,
    ensure_commande_mutable,
    generate_numero_commande,
    get_commande_owned,
    get_owned_ligne,
    lock_commande,
    recompute_commande_total,
    release_ligne_reservation,
    release_stock,
    reserve_stock,
)

router = APIRouter(prefix="/orders", tags=["orders"])
logger = logging.getLogger("caribooks.orders")

commande_crud = CrudBase[models.Commande](models.Commande, "id_commande")


@router.get("/commandes", response_model=list[CommandeRead])
def list_commandes(db: DbSession, current_user: CurrentUser):
    return db.query(models.Commande).filter(models.Commande.id_utilisateur == current_user.id_utilisateur).all()


@router.get("/commandes/{id_commande}", response_model=CommandeRead)
def get_commande(id_commande: int, db: DbSession, current_user: CurrentUser):
    cleanup_expired_carts(db)
    obj = get_commande_owned(db, id_commande, int(current_user.id_utilisateur))
    if obj is None:
        raise HTTPException(status_code=404, detail="Commande introuvable.")
    return attach_seconds_left(db, obj)


@router.post("/commandes", response_model=CommandeRead, status_code=status.HTTP_201_CREATED)
def create_commande(payload: CommandeCreate, db: DbSession, current_user: CurrentUser):
    cleanup_expired_carts(db)
    shipping_method = (payload.shipping_method or "POST").upper()
    if shipping_method not in SHIPPING_FEES_CHF:
        raise HTTPException(status_code=400, detail="Mode de livraison invalide.")
    # One cart per customer: drop any previous open cart (and give its reserved
    # stock straight back) before opening this one — see
    # order_service.cancel_other_open_commandes for the bug this fixes.
    abandoned = cancel_other_open_commandes(db, int(current_user.id_utilisateur))
    if abandoned:
        logger.info(
            "create_commande: cancelled %s abandoned cart(s) for user=%s",
            abandoned,
            current_user.id_utilisateur,
        )
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
    db: DbSession,
    current_user: CurrentUser,
):
    obj = get_commande_owned(db, id_commande, int(current_user.id_utilisateur))
    if obj is None:
        raise HTTPException(status_code=404, detail="Commande introuvable.")
    # Changing the shipping method changes frais_port_chf, so it re-totals the
    # commande — take the same lock every other cart mutation takes.
    obj = lock_commande(db, id_commande) or obj
    ensure_commande_mutable(obj)
    data = payload.model_dump(exclude_unset=True)
    shipping_method = data.pop("shipping_method", None)
    if shipping_method is not None:
        shipping_method = shipping_method.upper()
        if shipping_method not in SHIPPING_FEES_CHF:
            raise HTTPException(status_code=400, detail="Mode de livraison invalide.")
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
def cancel_own_commande(id_commande: int, db: DbSession, current_user: CurrentUser):
    """Customer-facing cancel: releases the cart reservation immediately instead
    of leaving stock reserved for the full 20-minute cart_expires_at window."""
    obj = get_commande_owned(db, id_commande, int(current_user.id_utilisateur))
    if obj is None:
        raise HTTPException(status_code=404, detail="Commande introuvable.")
    # Lock first: a cancel released stock concurrently with an in-flight
    # add-to-cart could otherwise release a reservation the other request was
    # still creating, leaving quantite_reservee permanently above zero.
    obj = lock_commande(db, id_commande) or obj
    cancel_commande(db, obj)
    db.commit()
    db.refresh(obj)
    return attach_seconds_left(db, obj)


@router.delete("/commandes/{id_commande}", status_code=status.HTTP_204_NO_CONTENT)
def delete_commande(id_commande: int, db: DbSession, current_user: CurrentUser):
    obj = get_commande_owned(db, id_commande, int(current_user.id_utilisateur))
    if obj is None:
        raise HTTPException(status_code=404, detail="Commande introuvable.")
    obj = lock_commande(db, id_commande) or obj
    cur = (obj.statut or "").upper()
    if cur in ("CREATED", "PENDING"):
        # Release any reserved stock before deleting — otherwise the cascade
        # delete of the lignes silently leaks the reservation forever.
        lignes = db.query(models.LigneCommande).filter(models.LigneCommande.id_commande == id_commande).all()
        for ligne in lignes:
            release_ligne_reservation(db, ligne)
    db.delete(obj)
    db.commit()
    return None


@router.get("/lignes", response_model=list[LigneCommandeRead])
def list_lignes(db: DbSession, current_user: CurrentUser):
    return (
        db.query(models.LigneCommande)
        .join(models.Commande, models.LigneCommande.id_commande == models.Commande.id_commande)
        .filter(models.Commande.id_utilisateur == current_user.id_utilisateur)
        .all()
    )


@router.get("/lignes/{id_ligne_commande}", response_model=LigneCommandeRead)
def get_ligne(id_ligne_commande: int, db: DbSession, current_user: CurrentUser):
    obj = get_owned_ligne(db, id_ligne_commande, int(current_user.id_utilisateur))
    if obj is None:
        raise HTTPException(status_code=404, detail="Ligne de commande introuvable.")
    return obj


@router.post("/lignes", response_model=LigneCommandeRead, status_code=status.HTTP_201_CREATED)
def create_ligne(payload: LigneCommandeCreate, db: DbSession, current_user: CurrentUser):
    cleanup_expired_carts(db)
    c = get_commande_owned(db, payload.id_commande, int(current_user.id_utilisateur))
    if c is None:
        raise HTTPException(status_code=404, detail="Commande introuvable.")
    # Ownership is checked above; the lock (taken before any stock row is
    # touched) is what serializes concurrent adds to the same cart. See
    # order_service.lock_commande: without it the totals raced and the stock
    # locks deadlocked.
    c = lock_commande(db, int(payload.id_commande)) or c
    if (c.statut or "").upper() in ("CANCELLED", "FAILED"):
        raise HTTPException(status_code=409, detail="Votre réservation a expiré. Retournez au panier.")
    ensure_commande_mutable(c)
    livre = db.query(models.Livre).filter(models.Livre.id_livre == payload.id_livre).first()
    if livre is None:
        raise HTTPException(status_code=404, detail="Livre introuvable.")
    # Unit price always comes from the catalog, never the client — otherwise a
    # tampered request body could set an arbitrary prix_unitaire_chf.
    unit_price = float(livre.prix_chf)  # type: ignore[arg-type]
    try:
        reserve_stock(db, int(payload.id_livre), int(payload.quantite))

        # Adding a livre already in this cart bumps the existing ligne instead of
        # creating a second row for it. A retried/double-submitted checkout used
        # to produce two lignes for the same book, which the cart UI (keyed by
        # id_livre) could not show or remove — the customer saw one copy and was
        # charged for two.
        obj = (
            db.query(models.LigneCommande)
            .filter(
                models.LigneCommande.id_commande == payload.id_commande,
                models.LigneCommande.id_livre == payload.id_livre,
            )
            .first()
        )
        if obj is not None:
            obj.quantite = int(obj.quantite) + int(payload.quantite)  # type: ignore[assignment]
            obj.prix_unitaire_chf = unit_price  # type: ignore[assignment]
        else:
            obj = models.LigneCommande(
                id_commande=payload.id_commande,
                id_livre=payload.id_livre,
                quantite=payload.quantite,
                prix_unitaire_chf=unit_price,
            )
            db.add(obj)

        # NOTE: we intentionally do NOT set livre.actif = False here.
        # Reserving stock for a cart (which may be abandoned) must not delist the
        # book from the catalogue. The book is only marked inactive when the
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
        logger.exception("Could not create ligne")
        raise HTTPException(status_code=500, detail="Impossible d’ajouter cet article à la commande.") from e


@router.put("/lignes/{id_ligne_commande}", response_model=LigneCommandeRead)
def update_ligne(
    id_ligne_commande: int,
    payload: LigneCommandeUpdate,
    db: DbSession,
    current_user: CurrentUser,
):
    obj = get_owned_ligne(db, id_ligne_commande, int(current_user.id_utilisateur))
    if obj is None:
        raise HTTPException(status_code=404, detail="Ligne de commande introuvable.")
    # Same lock-the-cart-first rule as create_ligne (see order_service.lock_commande).
    parent = lock_commande(db, int(obj.id_commande))
    if parent is not None:
        ensure_commande_mutable(parent)
    data = payload.model_dump(exclude_unset=True)
    new_qty = data.get("quantite")
    try:
        if new_qty is not None and int(new_qty) != int(obj.quantite):  # type: ignore[arg-type]
            delta = int(new_qty) - int(obj.quantite)  # type: ignore[arg-type]
            if delta > 0:
                reserve_stock(db, int(obj.id_livre), delta)  # type: ignore[arg-type]
            else:
                release_stock(db, int(obj.id_livre), -delta)  # type: ignore[arg-type]
            obj.quantite = int(new_qty)  # type: ignore[assignment]

        db.flush()
        if parent is not None:
            recompute_commande_total(db, parent)
        db.commit()
        db.refresh(obj)
        return obj
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.exception("Could not update ligne")
        raise HTTPException(status_code=500, detail="Impossible de modifier cette ligne de commande.") from e


@router.delete("/lignes/{id_ligne_commande}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ligne(id_ligne_commande: int, db: DbSession, current_user: CurrentUser):
    obj = get_owned_ligne(db, id_ligne_commande, int(current_user.id_utilisateur))
    if obj is None:
        raise HTTPException(status_code=404, detail="Ligne de commande introuvable.")
    id_commande = int(obj.id_commande)  # type: ignore[arg-type]
    # Same lock-the-cart-first rule as create_ligne (see order_service.lock_commande).
    commande = lock_commande(db, id_commande)
    if commande is None:
        raise HTTPException(status_code=404, detail="Commande introuvable.")
    ensure_commande_mutable(commande)
    if (commande.statut or "").upper() in ("CREATED", "PENDING"):
        # Release the reservation before deleting — otherwise it leaks forever.
        release_ligne_reservation(db, obj)
    db.delete(obj)
    db.flush()
    recompute_commande_total(db, commande)
    db.commit()
    return None
