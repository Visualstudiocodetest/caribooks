"""Business logic for orders/cart/stock reservation.

Kept separate from presentation/order_router.py (and order_admin_router.py) so
the routers stay thin HTTP adapters — this module owns the actual rules around
stock reservation, cart expiry, order totals, and finalization/refund/cancel.
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from sqlalchemy import text

from infrastructure import models


def _chf(value) -> float:
    """Quantize a monetary value to 2 decimals (CHF) using Decimal to avoid binary
    float drift when summing line totals + shipping, then return a plain float so
    the JSON API contract (numbers, not strings) is unchanged."""
    return float(Decimal(str(value or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

# Server-side source of truth for shipping fees — the client only chooses a
# shipping_method, never the fee itself (previously the fee was accepted
# directly from the client, allowing e.g. shipping_method=POST with
# frais_port_chf=0 to skip the real fee).
SHIPPING_FEES_CHF = {"POST": 9.0, "CLICK_COLLECT": 1.0}

# Single source of truth for the commande status vocabulary. Kept here (the
# order-domain service) so routers, cleanup and finalize all agree instead of
# each hard-coding its own tuple of magic strings.
# OPEN: cart still mutable and still subject to the 20-min expiry.
OPEN_STATUSES = {"CREATED", "PENDING"}
# PAID+: payment captured; stock has been (or is being) finalized. An order in
# any of these must never be auto-cancelled by the cart-expiry cleanup.
PAID_STATUSES = {"PAID", "CAPTURED", "COMPLETED", "SENT", "AT_RECEPTION", "FINISHED"}
# Terminal states from which nothing further should be finalized.
TERMINAL_STATUSES = {"CANCELLED", "REFUNDED"}


def generate_numero_commande(db: Session) -> str:
    """Server-side, collision-resistant order number: CMD-YYYYMMDD-XXXXXXXX.

    Uses a UUID suffix (unguessable, no client input) and the DB clock for the date
    part. Retries on the rare UUID collision. Replaces the previous behaviour of
    trusting a client-supplied numero_commande (predictable + IntegrityError → 500).
    """
    import uuid

    row = db.execute(text("SELECT DATE_FORMAT(NOW(), '%Y%m%d')")).scalar()
    day = str(row) if row else "00000000"
    for _ in range(5):
        candidate = f"CMD-{day}-{uuid.uuid4().hex[:8].upper()}"
        exists = (
            db.query(models.Commande.id_commande)
            .filter(models.Commande.numero_commande == candidate)
            .first()
        )
        if exists is None:
            return candidate
    # Extremely unlikely; fall back to a full UUID so we never 500 on collision.
    return f"CMD-{day}-{uuid.uuid4().hex.upper()}"


def get_commande_owned(db: Session, id_commande: int, id_utilisateur: int) -> models.Commande | None:
    return (
        db.query(models.Commande)
        .filter(models.Commande.id_commande == id_commande, models.Commande.id_utilisateur == id_utilisateur)
        .first()
    )


def ensure_commande_mutable(commande: models.Commande) -> None:
    """Guard: an order's lines, totals and shipping may only change while it is
    still an open cart (CREATED/PENDING).

    Previously the routers only blocked CANCELLED/FAILED, so a customer could add
    lines to or re-total an order that was already PAID. Anything not in
    OPEN_STATUSES (paid, shipped, cancelled, refunded…) is now rejected.
    """
    if (commande.statut or "").upper() not in OPEN_STATUSES:
        raise HTTPException(status_code=409, detail="Commande no longer modifiable in its current state")


def recompute_commande_total(db: Session, commande: models.Commande) -> None:
    """Recompute montant_total_chf from the commande's own lignes + shipping fee.

    Called any time a ligne is created/updated/deleted or the shipping method
    changes, so the persisted total always reflects server-authoritative
    prices — never a client-supplied value.
    """
    lignes_total = (
        db.query(func.sum(models.LigneCommande.prix_unitaire_chf * models.LigneCommande.quantite))
        .filter(models.LigneCommande.id_commande == commande.id_commande)
        .scalar()
    ) or 0
    commande.montant_total_chf = _chf(Decimal(str(lignes_total)) + Decimal(str(commande.frais_port_chf or 0)))  # type: ignore[assignment]


def _reactivate_article_if_available(db: Session, id_article: int) -> None:
    avail = (
        db.query(func.sum(models.Stock.quantite_disponible - models.Stock.quantite_reservee))
        .filter(models.Stock.id_article == id_article)
        .scalar()
        or 0
    )
    if avail > 0:
        art = db.query(models.Article).filter(models.Article.id_article == id_article).first()
        if art and not art.actif:
            art.actif = True  # type: ignore[assignment]


def release_ligne_reservation(db: Session, ligne: models.LigneCommande) -> None:
    """Reverse the quantite_reservee increment made when this single ligne was
    added to a cart. Used both by release_cart_reservation (whole commande)
    and directly when a single ligne is deleted, so stock is never leaked."""
    stocks = (
        db.query(models.Stock)
        .filter(models.Stock.id_article == ligne.id_article)
        .order_by(models.Stock.id_stock.asc())
        .with_for_update()
        .all()
    )
    remaining = int(ligne.quantite)  # type: ignore[arg-type]
    for s in stocks:
        if remaining <= 0:
            break
        release = min(int(s.quantite_reservee or 0), remaining)
        if release > 0:
            s.quantite_reservee = int(s.quantite_reservee or 0) - release  # type: ignore[assignment]
            remaining -= release
    _reactivate_article_if_available(db, int(ligne.id_article))  # type: ignore[arg-type]


def release_cart_reservation(db: Session, id_commande: int) -> None:
    """Reverse quantite_reservee increments made when lignes were added to a cart."""
    lignes = db.query(models.LigneCommande).filter(models.LigneCommande.id_commande == id_commande).all()
    for l in lignes:
        release_ligne_reservation(db, l)


def cleanup_expired_carts(db: Session) -> None:
    """Cancel CREATED/PENDING commandes whose cart reservation window has passed.

    The comparison uses the database clock (func.now()) so it is consistent with
    how cart_expires_at is set (also via the DB clock) — no Python/MySQL timezone
    drift.
    """
    expired = (
        db.query(models.Commande)
        .filter(
            models.Commande.statut.in_(list(OPEN_STATUSES)),
            models.Commande.cart_expires_at.isnot(None),
            models.Commande.cart_expires_at < func.now(),
        )
        .all()
    )
    for c in expired:
        release_cart_reservation(db, int(c.id_commande))
        c.statut = "CANCELLED"  # type: ignore[assignment]
    if expired:
        db.commit()


def attach_seconds_left(db: Session, commande: models.Commande) -> models.Commande:
    """Attach `cart_seconds_left` (computed with the DB clock) for a timezone-proof
    client-side countdown. Negative/None values mean expired or no reservation."""
    secs = None
    try:
        secs = db.execute(
            text(
                "SELECT TIMESTAMPDIFF(SECOND, NOW(), cart_expires_at) "
                "FROM commande WHERE id_commande = :id"
            ),
            {"id": int(commande.id_commande)},  # type: ignore[arg-type]
        ).scalar()
    except Exception:
        secs = None
    commande.cart_seconds_left = int(secs) if secs is not None else None  # type: ignore[attr-defined]
    return commande


def cancel_commande(db: Session, commande: models.Commande) -> None:
    """Cancel an order: release any cart reservation and mark CANCELLED.

    Shared by the customer-facing cancel endpoint and the admin one, so both
    release stock the same way instead of leaving a reservation to expire
    on its own over the next 20 minutes.
    """
    cur = (commande.statut or "").upper()
    if cur in ("FINISHED", "CANCELLED", "REFUNDED"):
        raise HTTPException(status_code=400, detail="Commande already in terminal state")
    if cur in ("CREATED", "PENDING"):
        release_cart_reservation(db, int(commande.id_commande))  # type: ignore[arg-type]
    commande.statut = "CANCELLED"  # type: ignore[assignment]


def finalize_commande(db: Session, id_commande: int) -> None:
    """Turn a paid order's reserved stock into sold stock and mark it PAID.

    Idempotent and concurrency-safe: the commande row is locked FOR UPDATE and, if
    it is already in a PAID+/terminal state, we return without touching stock again.
    This is what makes the four payment callbacks (confirm / poll / webhook / local
    webhook) safe to fire concurrently — the first to acquire the lock finalizes and
    flips the status to PAID; every later caller sees PAID and no-ops, so stock is
    decremented exactly once (previously each path could double-decrement).

    It also sets `commande.statut = "PAID"` and clears `cart_expires_at`, so the
    cart-expiry cleanup can never cancel an order that has actually been paid.
    """
    commande = (
        db.query(models.Commande)
        .filter(models.Commande.id_commande == id_commande)
        .with_for_update()
        .first()
    )
    if commande is None:
        return
    if (commande.statut or "").upper() not in OPEN_STATUSES:
        # Already finalized (PAID+) or terminal (CANCELLED/REFUNDED) — nothing to do.
        return

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
    # mark articles inactive if no stock left (only those in this order)
    art_ids = [l.id_article for l in lignes]
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

    # Mark the order paid and drop the cart-expiry deadline so cleanup_expired_carts
    # can no longer cancel it. Admins advance PAID -> SENT/AT_RECEPTION/FINISHED later.
    commande.statut = "PAID"  # type: ignore[assignment]
    commande.cart_expires_at = None  # type: ignore[assignment]


def refund_commande(db: Session, id_commande: int) -> None:
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


def load_commande_context(db: Session, id_commande: int, id_utilisateur: int):
    commande = get_commande_owned(db, id_commande, id_utilisateur)
    if commande is None:
        return None, None, None

    lignes = (
        db.query(models.LigneCommande)
        .filter(models.LigneCommande.id_commande == id_commande)
        .all()
    )
    for ligne in lignes:
        if getattr(ligne, "article", None) is None:
            ligne.article = db.query(models.Article).filter(models.Article.id_article == ligne.id_article).first()

    user = db.query(models.Utilisateur).filter(models.Utilisateur.id_utilisateur == id_utilisateur).first()
    return commande, lignes, user
