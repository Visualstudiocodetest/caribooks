"""Business logic for orders/cart/stock reservation.

Kept separate from presentation/order_router.py (and order_admin_router.py) so
the routers stay thin HTTP adapters — this module owns the actual rules around
stock reservation, cart expiry, order totals, and finalization/refund/cancel.
"""

from __future__ import annotations

import logging
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from infrastructure import models

logger = logging.getLogger("caribooks.orders")


def _chf(value) -> float:
    """Quantize a monetary value to 2 decimals (CHF) using Decimal to avoid binary
    float drift when summing line totals + shipping, then return a plain float so
    the JSON API contract (numbers, not strings) is unchanged."""
    return float(Decimal(str(value or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


SHIPPING_FEES_CHF = {"POST": 9.0, "CLICK_COLLECT": 1.0}


OPEN_STATUSES = {"CREATED", "PENDING"}

PAID_STATUSES = {"PAID", "CAPTURED", "COMPLETED", "SENT", "AT_RECEPTION", "FINISHED"}

TERMINAL_STATUSES = {"CANCELLED", "REFUNDED"}
ALL_STATUSES = OPEN_STATUSES | PAID_STATUSES | TERMINAL_STATUSES

PAID_NOT_ADVANCED_STATUSES = {"PAID", "CAPTURED", "COMPLETED"}

# Orders that still require follow-up (payment, shipping, delivery) — an account
# cannot be anonymized while one of its orders is in one of these states, since
# doing so would sever the paper trail before the transaction is actually closed.
STATUSES_BLOCKING_ACCOUNT_DELETION = ALL_STATUSES - TERMINAL_STATUSES - {"FINISHED"}


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


def has_orders_blocking_deletion(db: Session, id_utilisateur: int) -> bool:
    """True if the user has an order still in progress (unpaid, paid-not-yet-
    finished, or shipping) — account anonymization must be refused until those
    reach a terminal state (FINISHED/CANCELLED/REFUNDED)."""
    return (
        db.query(models.Commande.id_commande)
        .filter(
            models.Commande.id_utilisateur == id_utilisateur,
            models.Commande.statut.in_(list(STATUSES_BLOCKING_ACCOUNT_DELETION)),
        )
        .first()
        is not None
    )


def get_owned_ligne(db: Session, id_ligne_commande: int, id_utilisateur: int) -> models.LigneCommande | None:
    """A LigneCommande belongs to whoever owns its parent Commande — there's no
    id_utilisateur column on the line itself, hence the join. Shared by every
    single-ligne lookup in order_router.py (get/update/delete) instead of each
    repeating the same join+filter."""
    return (
        db.query(models.LigneCommande)
        .join(models.Commande, models.LigneCommande.id_commande == models.Commande.id_commande)
        .filter(
            models.LigneCommande.id_ligne_commande == id_ligne_commande,
            models.Commande.id_utilisateur == id_utilisateur,
        )
        .first()
    )


def get_owned_paiement(db: Session, id_paiement: int, id_utilisateur: int) -> models.Paiement | None:
    """Same idea as get_owned_ligne, for Paiement: ownership flows through the
    parent Commande. Shared by every single-paiement lookup in
    payment_router.py that isn't the admin-only update/delete."""
    return (
        db.query(models.Paiement)
        .join(models.Commande, models.Paiement.id_commande == models.Commande.id_commande)
        .filter(
            models.Paiement.id_paiement == id_paiement,
            models.Commande.id_utilisateur == id_utilisateur,
        )
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


def _lock_stock_rows(db: Session, id_article: int) -> list[models.Stock]:
    """Lock (FOR UPDATE) all stock rows for an article, oldest first. Shared by
    every stock mutation (reserve/release/finalize/refund) so concurrent
    requests for the same article always serialize on the same row order."""
    return (
        db.query(models.Stock)
        .filter(models.Stock.id_article == id_article)
        .order_by(models.Stock.id_stock.asc())
        .with_for_update()
        .all()
    )


def reserve_stock(db: Session, id_article: int, quantity: int) -> None:
    """Reserve `quantity` units of an article across its stock rows.

    Raises HTTPException(400) if not enough stock is available. Used when a
    ligne is created or its quantity is increased.
    """
    stocks = _lock_stock_rows(db, id_article)
    if not stocks:
        return
    total_available = sum((s.quantite_disponible or 0) - (s.quantite_reservee or 0) for s in stocks)
    if quantity > total_available:  # type: ignore[operator]
        raise HTTPException(status_code=400, detail="Not enough stock")
    remaining = quantity
    for s in stocks:
        if remaining <= 0:  # type: ignore[operator]
            break
        avail = (s.quantite_disponible or 0) - (s.quantite_reservee or 0)  # type: ignore[operator]
        take = min(avail, remaining)  # type: ignore[type-var]
        if take <= 0:  # type: ignore[operator]
            continue
        s.quantite_reservee = (s.quantite_reservee or 0) + take  # type: ignore[assignment]
        remaining -= take


def release_stock(db: Session, id_article: int, quantity: int) -> None:
    """Release `quantity` previously-reserved units of an article back to
    availability. Used when a ligne is deleted or its quantity is decreased."""
    stocks = _lock_stock_rows(db, id_article)
    remaining = quantity
    for s in stocks:
        if remaining <= 0:  # type: ignore[operator]
            break
        cur_res = s.quantite_reservee or 0  # type: ignore[operator]
        give_back = min(cur_res, remaining)  # type: ignore[type-var]
        if give_back <= 0:  # type: ignore[operator]
            continue
        s.quantite_reservee = cur_res - give_back  # type: ignore[assignment]
        remaining -= give_back


def build_pending_paiement(payload: Any, commande: models.Commande) -> models.Paiement:
    """A payment always starts PENDING with the commande's own server-computed
    total — never a client-supplied amount/status. It can only ever transition to
    a paid state via a verified PostFinance callback (see order_router.py)."""
    return models.Paiement(
        id_commande=payload.id_commande,
        fournisseur_paiement=payload.fournisseur_paiement or "POSTFINANCE",
        reference_externe=payload.reference_externe,
        montant_chf=float(commande.montant_total_chf),  # type: ignore[arg-type]
        devise=payload.devise,
        statut="PENDING",
        date_paiement=payload.date_paiement,
    )


def _reactivate_article_if_available(db: Session, id_article: int) -> None:
    avail = (
        db.query(func.sum(models.Stock.quantite_disponible - models.Stock.quantite_reservee))
        .filter(models.Stock.id_article == id_article)
        .scalar()
        or 0
    )
    if avail > 0:
        art = db.query(models.Article).filter(models.Article.id_article == id_article).first()
        if art and not art.actif: # type: ignore[assignment]
            art.actif = True  # type: ignore[assignment]


def release_ligne_reservation(db: Session, ligne: models.LigneCommande) -> None:
    """Reverse the quantite_reservee increment made when this single ligne was
    added to a cart. Used both by release_cart_reservation (whole commande)
    and directly when a single ligne is deleted, so stock is never leaked."""
    release_stock(db, int(ligne.id_article), int(ligne.quantite))  # type: ignore[arg-type]
    _reactivate_article_if_available(db, int(ligne.id_article))  # type: ignore[arg-type]


def release_cart_reservation(db: Session, id_commande: int) -> None:
    """Reverse quantite_reservee increments made when lignes were added to a cart."""
    lignes = db.query(models.LigneCommande).filter(models.LigneCommande.id_commande == id_commande).all()
    for ligne in lignes:
        release_ligne_reservation(db, ligne)


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
        release_cart_reservation(db, int(c.id_commande)) # type: ignore[assignment]
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
    for ligne in lignes:
        stocks = _lock_stock_rows(db, int(ligne.id_article))  # type: ignore[arg-type]
        if not stocks:
            # nothing to do if no stock rows exist
            continue
        remaining = ligne.quantite
        # first reduce reserved counts where possible -- this only releases the
        # cart-time hold (quantite_reservee), it does NOT touch
        # quantite_disponible (see the "quantite_disponible is untouched"
        # tests below): the unit was never subtracted from the physical count
        # in the first place, so there is nothing here for a refund to give
        # back. Only the fallback loop below actually removes physical stock,
        # which is why only *that* gets recorded as a StockMouvement.
        for s in stocks:
            if remaining <= 0:  # type: ignore
                break
            reserve = s.quantite_reservee or 0  # type: ignore
            take_from_reserve = min(reserve, remaining)  # type: ignore
            if take_from_reserve > 0:  # type: ignore
                s.quantite_reservee = reserve - take_from_reserve  # type: ignore
                remaining -= take_from_reserve
        # if still remaining (not fully covered by an existing reservation),
        # deduct from available quantities -- this is a real, permanent
        # reduction of physical stock, so record exactly which row(s) and how
        # much, so a refund can reverse precisely this.
        for s in stocks:
            if remaining <= 0:  # type: ignore
                break
            avail = s.quantite_disponible or 0  # type: ignore
            take = min(avail, remaining)  # type: ignore
            if take <= 0:  # type: ignore
                continue
            s.quantite_disponible = avail - take  # type: ignore
            remaining -= take
            db.add(models.StockMouvement(id_ligne_commande=ligne.id_ligne_commande, id_stock=s.id_stock, quantite=take))
    # mark articles inactive if no stock left (only those in this order)
    art_ids = [ligne.id_article for ligne in lignes]
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
    """Return sold stock back to availability.

    Prefers an exact reversal via the StockMouvement rows finalize_commande
    wrote: each one says precisely which Stock row (and how much) a ligne's
    sale came from, so quantite_disponible is credited back there — not to
    whichever row happens to be first for the article. The previous behaviour
    credited the *entire* refund to a single arbitrary row: the total
    available-for-sale count stayed correct either way (it's a plain sum),
    but which source_stock the stock was attributed to drifted with every
    refund.

    Falls back to that old "credit the first row" behaviour only for a ligne
    with no recorded mouvements (an order paid before this tracking existed) —
    logged, since it's the imprecise path.
    """
    lignes = db.query(models.LigneCommande).filter(models.LigneCommande.id_commande == id_commande).all()
    for ligne in lignes:
        mouvements = (
            db.query(models.StockMouvement)
            .filter(models.StockMouvement.id_ligne_commande == ligne.id_ligne_commande)
            .all()
        )
        if mouvements:
            stock_ids = [int(m.id_stock) for m in mouvements]  # type: ignore[arg-type]
            stocks_by_id = {
                int(s.id_stock): s  # type: ignore[arg-type]
                for s in db.query(models.Stock)
                .filter(models.Stock.id_stock.in_(stock_ids))
                .order_by(models.Stock.id_stock.asc())
                .with_for_update()
                .all()
            }
            for m in mouvements:
                s = stocks_by_id.get(int(m.id_stock))  # type: ignore[arg-type]
                if s is not None:
                    s.quantite_disponible = (s.quantite_disponible or 0) + m.quantite  # type: ignore[operator]
                db.delete(m)
            continue

        # No tracked mouvement for this ligne (paid before StockMouvement
        # existed) -- best-effort fallback, same behaviour as before.
        stocks = _lock_stock_rows(db, int(ligne.id_article))  # type: ignore[arg-type]
        if not stocks:
            continue
        logger.warning(
            "refund_commande: no StockMouvement for ligne=%s (article=%s) -- crediting "
            "qty=%s to a single row (pre-tracking order, best-effort fallback)",
            ligne.id_ligne_commande,
            ligne.id_article,
            ligne.quantite,
        )
        stocks[0].quantite_disponible = (stocks[0].quantite_disponible or 0) + ligne.quantite  # type: ignore[operator]
    for aid in {ligne.id_article for ligne in lignes}:
        _reactivate_article_if_available(db, int(aid))  # type: ignore[arg-type]


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
