from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from  infrastructure import models
from  infrastructure.crud_base import CrudBase
from  presentation.deps import get_current_user, get_db
from  presentation.deps import require_admin
from  presentation.schemas import (
    CommandeCreate,
    CommandeRead,
    CommandeUpdate,
    LigneCommandeCreate,
    LigneCommandeRead,
    LigneCommandeUpdate,
    PaiementCreate,
    PaiementRead,
    PaiementUpdate,
)
from services.postfinance_service import (
    create_postfinance_checkout,
    parse_postfinance_webhook,
    verify_postfinance_webhook_signature,
    get_postfinance_checkout_status,
)
from fastapi import Request
import os
import hmac
import hashlib
from datetime import datetime

router = APIRouter(prefix="/orders", tags=["orders"])

commande_crud = CrudBase[models.Commande](models.Commande, "id_commande")
ligne_crud = CrudBase[models.LigneCommande](models.LigneCommande, "id_ligne_commande")
paiement_crud = CrudBase[models.Paiement](models.Paiement, "id_paiement")


def _get_commande_owned(db: Session, id_commande: int, id_utilisateur: int) -> models.Commande | None:
    return (
        db.query(models.Commande)
        .filter(models.Commande.id_commande == id_commande, models.Commande.id_utilisateur == id_utilisateur)
        .first()
    )


def _finalize_commande(db: Session, id_commande: int):
    # For each ligne in the commande, finalize reserved stock into sold stock
    lignes = db.query(models.LigneCommande).filter(models.LigneCommande.id_commande == id_commande).all()
    for l in lignes:
        # find stock rows for the article
        stocks = (
            db.query(models.Stock)
            .filter(models.Stock.id_article == l.id_article)
            .order_by(models.Stock.id_stock.asc())
            .with_for_update()
            .all()
        )
        if not stocks:
            # nothing to do if no stock rows exist
            continue
        remaining = l.quantite
        # first reduce reserved counts where possible
        for s in stocks:
            if remaining <= 0:  # type: ignore
                break
            reserve = s.quantite_reservee or 0  # type: ignore
            take_from_reserve = min(reserve, remaining)  # type: ignore
            if take_from_reserve > 0:  # type: ignore
                s.quantite_reservee = reserve - take_from_reserve  # type: ignore
                remaining -= take_from_reserve
        # if still remaining, deduct from available quantities
        for s in stocks:
            if remaining <= 0:  # type: ignore
                break
            avail = s.quantite_disponible or 0  # type: ignore
            take = min(avail, remaining)  # type: ignore
            if take <= 0:  # type: ignore
                continue
            s.quantite_disponible = avail - take  # type: ignore
            remaining -= take
    # mark articles inactive if no stock left
    art_ids = [a.id_article for a in db.query(models.Article).all()]
    for aid in art_ids:
        total_left = (
            db.query(models.Stock)
            .filter(models.Stock.id_article == aid)
            .with_entities(func.sum(models.Stock.quantite_disponible))
            .scalar()
        )
        if not total_left:  # type: ignore
            art = db.query(models.Article).filter(models.Article.id_article == aid).first()
            if art:
                art.actif = False  # type: ignore


def _refund_commande(db: Session, id_commande: int):
    # When refunding, return sold quantities back to stock
    lignes = db.query(models.LigneCommande).filter(models.LigneCommande.id_commande == id_commande).all()
    for l in lignes:
        stocks = (
            db.query(models.Stock)
            .filter(models.Stock.id_article == l.id_article)
            .order_by(models.Stock.id_stock.asc())
            .with_for_update()
            .all()
        )
        if not stocks:  # type: ignore
            continue
        remaining = l.quantite
        # add back to first stock rows
        for s in stocks:
            if remaining <= 0:  # type: ignore
                break
            s.quantite_disponible = (s.quantite_disponible or 0) + remaining  # type: ignore
            remaining = 0
    # reactivate articles that have stock
    for aid in {l.id_article for l in lignes}:
        total_left = (
            db.query(models.Stock)
            .filter(models.Stock.id_article == aid)
            .with_entities(func.sum(models.Stock.quantite_disponible))
            .scalar()
        )
        if total_left and total_left > 0:  # type: ignore
            art = db.query(models.Article).filter(models.Article.id_article == aid).first()
            if art:
                art.actif = True  # type: ignore


@router.get("/commandes", response_model=list[CommandeRead])
def list_commandes(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return db.query(models.Commande).filter(models.Commande.id_utilisateur == current_user.id_utilisateur).all()


@router.get("/commandes/{id_commande}", response_model=CommandeRead)
def get_commande(id_commande: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    obj = _get_commande_owned(db, id_commande, int(current_user.id_utilisateur))
    if obj is None:
        raise HTTPException(status_code=404, detail="Commande not found")
    return obj


@router.post("/commandes", response_model=CommandeRead, status_code=status.HTTP_201_CREATED)
def create_commande(payload: CommandeCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    obj = models.Commande(id_utilisateur=current_user.id_utilisateur, **payload.model_dump())
    return commande_crud.create(db, obj)


@router.put("/commandes/{id_commande}", response_model=CommandeRead)
def update_commande(
    id_commande: int,
    payload: CommandeUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    obj = _get_commande_owned(db, id_commande, int(current_user.id_utilisateur))
    if obj is None:
        raise HTTPException(status_code=404, detail="Commande not found")
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        if hasattr(obj, k):
            setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/commandes/{id_commande}", status_code=status.HTTP_204_NO_CONTENT)
def delete_commande(id_commande: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    obj = _get_commande_owned(db, id_commande, int(current_user.id_utilisateur))
    if obj is None:
        raise HTTPException(status_code=404, detail="Commande not found")
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
    if _get_commande_owned(db, payload.id_commande, int(current_user.id_utilisateur)) is None:
        raise HTTPException(status_code=404, detail="Commande not found")
    try:
        # Lock stock rows for this article to prevent concurrent reservations
        stocks = (
            db.query(models.Stock)
            .filter(models.Stock.id_article == payload.id_article)
            .order_by(models.Stock.id_stock.asc())
            .with_for_update()
            .all()
        )

        if stocks:  # type: ignore
            # compute total available (available = quantite_disponible - quantite_reservee)
            total_available = sum((s.quantite_disponible or 0) - (s.quantite_reservee or 0) for s in stocks)  # type: ignore
            if payload.quantite > total_available:  # type: ignore
                raise HTTPException(status_code=400, detail="Not enough stock")

            # reserve across stock sources
            remaining = payload.quantite
            for s in stocks:
                if remaining <= 0:  # type: ignore
                    break
                avail = (s.quantite_disponible or 0) - (s.quantite_reservee or 0)  # type: ignore
                take = min(avail, remaining)  # type: ignore
                if take <= 0:  # type: ignore
                    continue
                s.quantite_reservee = (s.quantite_reservee or 0) + take  # type: ignore
                remaining -= take

        # create the ligne and commit once (for articles without stock rows, we allow creation)
        obj = models.LigneCommande(**payload.model_dump())
        db.add(obj)

        # If article now out of stock, mark inactive
        if stocks:  # type: ignore
            total_left = sum((s.quantite_disponible or 0) - (s.quantite_reservee or 0) for s in stocks)  # type: ignore
            if total_left <= 0:  # type: ignore
                art = db.query(models.Article).filter(models.Article.id_article == payload.id_article).first()
                if art:
                    art.actif = False  # type: ignore

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
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        if hasattr(obj, k):
            setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj


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
    db.delete(obj)
    db.commit()
    return None


@router.get("/paiements", response_model=list[PaiementRead])
def list_paiements(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return (
        db.query(models.Paiement)
        .join(models.Commande, models.Paiement.id_commande == models.Commande.id_commande)
        .filter(models.Commande.id_utilisateur == current_user.id_utilisateur)
        .all()
    )


@router.get("/paiements/{id_paiement}", response_model=PaiementRead)
def get_paiement(id_paiement: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    obj = (
        db.query(models.Paiement)
        .join(models.Commande, models.Paiement.id_commande == models.Commande.id_commande)
        .filter(models.Paiement.id_paiement == id_paiement, models.Commande.id_utilisateur == current_user.id_utilisateur)
        .first()
    )
    if obj is None:
        raise HTTPException(status_code=404, detail="Paiement not found")
    return obj


@router.post("/paiements", response_model=PaiementRead, status_code=status.HTTP_201_CREATED)
def create_paiement(payload: PaiementCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    if _get_commande_owned(db, payload.id_commande, int(current_user.id_utilisateur)) is None:
        raise HTTPException(status_code=404, detail="Commande not found")
    obj = models.Paiement(**payload.model_dump())
    created = paiement_crud.create(db, obj)
    # finalize immediately if payment is captured/paid
    try:
        if created.statut and str(created.statut).upper() in ("CAPTURED", "PAID", "COMPLETED"):  # type: ignore
            _finalize_commande(db, int(created.id_commande))  # type: ignore
            db.commit()
    except Exception:
        # don't fail payment creation on finalization errors
        db.rollback()
    return created


@router.post("/paiements/postfinance", status_code=status.HTTP_201_CREATED)
def create_paiement_postfinance(payload: PaiementCreate, request: Request, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    # Create local paiement record and request a PostFinance checkout session
    if _get_commande_owned(db, payload.id_commande, int(current_user.id_utilisateur)) is None:
        raise HTTPException(status_code=404, detail="Commande not found")

    user = db.query(models.Utilisateur).filter(models.Utilisateur.id_utilisateur == current_user.id_utilisateur).first()
    frontend_base_url = os.getenv("FRONTEND_BASE_URL", str(request.base_url).rstrip("/"))
    cancel_url = f"{frontend_base_url}/cart"

    # create local record with pending status
    obj = models.Paiement(**payload.model_dump())
    obj.fournisseur_paiement = payload.fournisseur_paiement or "POSTFINANCE"  # type: ignore[assignment]
    obj.statut = payload.statut or "PENDING"  # type: ignore[assignment]
    created = paiement_crud.create(db, obj)

    # build return URL including local paiement id so frontend can poll status
    return_url = f"{frontend_base_url}/payment?commandeId={payload.id_commande}&paiementId={created.id_paiement}"

    # call PostFinance service
    description = f"Commande {int(created.id_commande)}"  # type: ignore
    customer_email = str(getattr(user, "email", "")) if user is not None else None
    pf_resp = create_postfinance_checkout(
        float(created.montant_chf),  # type: ignore[arg-type]
        str(created.id_paiement),
        return_url,
        cancel_url,
        description,
        customer_email,
    )  # type: ignore

    # update reference_externe with provider id if available
    ref = pf_resp.get("id")
    if ref:
        created.reference_externe = str(ref)  # type: ignore[assignment]
    if pf_resp.get("status"):
        created.statut = str(pf_resp.get("status"))  # type: ignore[assignment]
    db.commit()
    db.refresh(created)

    return {
        "paiement": created,
        "redirect_url": pf_resp.get("redirect_url"),
        "raw": pf_resp.get("raw"),
        "error": pf_resp.get("error"),
    }


@router.get("/paiements/{id_paiement}/poll-postfinance")
def poll_paiement_postfinance(id_paiement: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """Poll PostFinance for the status of a payment (alternative to webhooks).

    This endpoint queries PostFinance using the stored `reference_externe` (link id)
    or falls back to searching by the local payment id. It updates the local payment
    status and finalizes the order if the payment is captured/paid.
    """
    obj = (
        db.query(models.Paiement)
        .join(models.Commande, models.Paiement.id_commande == models.Commande.id_commande)
        .filter(models.Paiement.id_paiement == id_paiement, models.Commande.id_utilisateur == current_user.id_utilisateur)
        .first()
    )
    if obj is None:
        raise HTTPException(status_code=404, detail="Paiement not found")

    provider_id = getattr(obj, "reference_externe", None)
    # Try to query provider by stored link id, else by local payment id
    pf_resp = get_postfinance_checkout_status(provider_id, str(obj.id_paiement))

    # If provider returned a status, update local record
    if pf_resp.get("status"):
        new_status = str(pf_resp.get("status"))
        obj.statut = new_status  # type: ignore
        if new_status and new_status.upper() in ("CAPTURED", "PAID", "COMPLETED", "AUTHORIZED", "FULFILL"):
            obj.date_paiement = datetime.utcnow()  # type: ignore
        db.commit()
        db.refresh(obj)

        try:
            if new_status and new_status.upper() in ("CAPTURED", "PAID", "COMPLETED", "AUTHORIZED", "FULFILL"):
                _finalize_commande(db, int(obj.id_commande))  # type: ignore
                db.commit()
        except Exception:
            db.rollback()

    return {"paiement": obj, "raw": pf_resp}


@router.post("/paiements/webhook/postfinance")
async def postfinance_webhook(request: Request, db: Session = Depends(get_db)):
    # PostFinance webhook signature verification
    sig_header = request.headers.get("x-signature") or request.headers.get("X-Signature")

    if not sig_header:
        raise HTTPException(status_code=403, detail="Missing webhook signature")

    raw_body = await request.body()
    if not verify_postfinance_webhook_signature(raw_body, sig_header):
        raise HTTPException(status_code=403, detail="Invalid webhook signature")

    payload = await request.json()

    parsed = parse_postfinance_webhook(payload)
    # try match by reference (merchantOrderId) or id
    ref = parsed.get("reference")
    pay_id = parsed.get("id")
    obj = None
    if ref:
        obj = db.query(models.Paiement).filter(models.Paiement.reference_externe == str(ref)).first()
    if obj is None and pay_id:
        obj = db.query(models.Paiement).filter(models.Paiement.reference_externe == str(pay_id)).first()
    if obj is None:
        # no matching payment; ignore
        return {"ok": False, "reason": "not_found"}

    new_status = parsed.get("status") or "UNKNOWN"
    obj.statut = new_status  # type: ignore
    obj.date_paiement = datetime.utcnow()  # type: ignore
    db.commit()
    db.refresh(obj)

    try:
        if new_status and str(new_status).upper() in ("CAPTURED", "PAID", "COMPLETED", "AUTHORIZED", "FULFILL"):
            _finalize_commande(db, int(obj.id_commande))  # type: ignore
            db.commit()
    except Exception:
        db.rollback()

    return {"ok": True}


@router.put("/paiements/{id_paiement}", response_model=PaiementRead)
def update_paiement(
    id_paiement: int,
    payload: PaiementUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    obj = (
        db.query(models.Paiement)
        .join(models.Commande, models.Paiement.id_commande == models.Commande.id_commande)
        .filter(models.Paiement.id_paiement == id_paiement, models.Commande.id_utilisateur == current_user.id_utilisateur)
        .first()
    )
    if obj is None:
        raise HTTPException(status_code=404, detail="Paiement not found")
    data = payload.model_dump(exclude_unset=True)
    prev_stat = str(obj.statut) if getattr(obj, "statut", None) else None
    for k, v in data.items():
        if hasattr(obj, k):
            setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    # handle statut transitions
    new_stat = getattr(obj, "statut", None)
    try:
        if prev_stat is None or prev_stat.upper() not in ("CAPTURED", "PAID", "COMPLETED"):
            if new_stat and new_stat.upper() in ("CAPTURED", "PAID", "COMPLETED"):
                _finalize_commande(db, int(obj.id_commande))  # type: ignore[arg-type]
                db.commit()
        # refund transition
        if prev_stat and prev_stat.upper() in ("CAPTURED", "PAID", "COMPLETED") and new_stat and new_stat.upper() == "REFUNDED":
            _refund_commande(db, int(obj.id_commande))  # type: ignore[arg-type]
            db.commit()
    except Exception:
        db.rollback()

    return obj


@router.delete("/paiements/{id_paiement}", status_code=status.HTTP_204_NO_CONTENT)
def delete_paiement(id_paiement: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    obj = (
        db.query(models.Paiement)
        .join(models.Commande, models.Paiement.id_commande == models.Commande.id_commande)
        .filter(models.Paiement.id_paiement == id_paiement, models.Commande.id_utilisateur == current_user.id_utilisateur)
        .first()
    )
    if obj is None:
        raise HTTPException(status_code=404, detail="Paiement not found")
    db.delete(obj)
    db.commit()
    return None


@router.get("/admin/commandes", response_model=list[CommandeRead])
def admin_list_commandes(db: Session = Depends(get_db), _admin=Depends(require_admin)):
    return db.query(models.Commande).all()


@router.put("/admin/commandes/{id_commande}/status", response_model=CommandeRead)
def admin_set_status(id_commande: int, payload: CommandeUpdate, db: Session = Depends(get_db), _admin=Depends(require_admin)):
    obj = db.query(models.Commande).filter(models.Commande.id_commande == id_commande).first()
    if obj is None:
        raise HTTPException(status_code=404, detail="Commande not found")
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        if hasattr(obj, k):
            setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj


@router.post("/admin/commandes/{id_commande}/advance", response_model=CommandeRead)
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

