from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy.orm import Session

from infrastructure import models
from infrastructure.crud_base import CrudBase
from presentation.deps import AdminUser, CurrentUser, DbSession
from presentation.schemas import PaiementCreate, PaiementRead, PaiementUpdate
from services.order_service import (
    build_pending_paiement,
    ensure_commande_mutable,
    finalize_commande,
    get_commande_owned,
    get_owned_paiement,
    load_commande_context,
)
from services.postfinance_service import (
    amount_matches_commande,
    build_postfinance_checkout_data,
    confirm_postfinance_transaction,
    create_postfinance_iframe_session,
    get_postfinance_checkout_status,
    get_postfinance_transaction,
    is_postfinance_success_status,
    parse_postfinance_webhook,
    verify_postfinance_webhook_signature,
)

logger = logging.getLogger("caribooks.orders")

router = APIRouter(prefix="/orders", tags=["orders-payments"])

paiement_crud = CrudBase[models.Paiement](models.Paiement, "id_paiement")


def _finalize_paid_order(db: Session, id_commande: int, source: str) -> bool:
    """Finalize a paid order's stock, committing on success.

    Shared by all four payment callbacks (confirm / poll / webhook / local webhook)
    so they finalize identically. `finalize_commande` is itself idempotent and row-
    locked, so concurrent callbacks decrement stock exactly once. On failure we log
    at error level (with the order id + which callback) instead of swallowing it —
    the payment is already captured, so a failed finalize needs manual reconciliation
    and must be visible in the logs, not silent.
    Returns True if finalize succeeded.
    """
    try:
        finalize_commande(db, int(id_commande))
        db.commit()
        return True
    except Exception:
        db.rollback()
        logger.error(
            "finalize_commande failed for commande=%s (source=%s): payment captured "
            "but stock/status not updated — needs reconciliation",
            id_commande,
            source,
            exc_info=True,
        )
        return False


def _assert_amount_matches_commande(db: Session, id_commande: int, provider_amount, source: str) -> None:
    """Refuse to finalize an order if the amount PostFinance reports for the
    transaction doesn't match the commande's own server-computed total.

    A verified webhook signature only proves the payload wasn't tampered with
    in transit; it doesn't protect against a misconfigured PostFinance space
    or an upstream bug associating the wrong transaction with our
    merchantReference. `provider_amount` of None (e.g. local/dev simulation)
    is treated as "can't verify" rather than a mismatch -- see
    amount_matches_commande.
    """
    commande = db.query(models.Commande).filter(models.Commande.id_commande == id_commande).first()
    if commande is None:
        return
    if not amount_matches_commande(float(commande.montant_total_chf), provider_amount):
        logger.error(
            "postfinance amount mismatch for commande=%s (source=%s): commande total=%.2f CHF, "
            "provider reported=%s -- refusing to finalize",
            id_commande,
            source,
            float(commande.montant_total_chf),
            provider_amount,
        )
        raise HTTPException(
            status_code=409,
            detail=(
                "Le montant du paiement ne correspond pas au total de la commande. "
                "Aucun débit n’a été effectué — reprenez votre commande depuis le panier."
            ),
        )


@router.get("/paiements", response_model=list[PaiementRead])
def list_paiements(db: DbSession, current_user: CurrentUser):
    return (
        db.query(models.Paiement)
        .join(models.Commande, models.Paiement.id_commande == models.Commande.id_commande)
        .filter(models.Commande.id_utilisateur == current_user.id_utilisateur)
        .all()
    )


@router.get("/paiements/{id_paiement}", response_model=PaiementRead)
def get_paiement(id_paiement: int, db: DbSession, current_user: CurrentUser):
    obj = get_owned_paiement(db, id_paiement, int(current_user.id_utilisateur))
    if obj is None:
        raise HTTPException(status_code=404, detail="Paiement introuvable.")
    return obj


@router.post("/paiements", response_model=PaiementRead, status_code=status.HTTP_201_CREATED)
def create_paiement(payload: PaiementCreate, db: DbSession, current_user: CurrentUser):
    commande = get_commande_owned(db, payload.id_commande, int(current_user.id_utilisateur))
    if commande is None:
        raise HTTPException(status_code=404, detail="Commande introuvable.")
    # See build_pending_paiement: a payment always starts PENDING with the
    # commande's own server-computed total, never a client-supplied one.
    return paiement_crud.create(db, build_pending_paiement(payload, commande))


@router.post("/paiements/postfinance", status_code=status.HTTP_201_CREATED)
def create_paiement_postfinance(
    payload: PaiementCreate,
    request: Request,
    db: DbSession,
    current_user: CurrentUser,
):
    """Create a local paiement and initialize a PostFinance iframe checkout session."""
    commande, lignes, user = load_commande_context(db, payload.id_commande, int(current_user.id_utilisateur))
    if commande is None:
        raise HTTPException(status_code=404, detail="Commande introuvable.")
    # An empty cart (or one whose lines were all released by cart expiry) has
    # nothing to charge: PostFinance rejects a zero-amount transaction with an
    # opaque provider error, so fail here with something the customer can act on.
    if not lignes:
        raise HTTPException(status_code=400, detail="Votre commande est vide. Ajoutez des articles avant de payer.")
    ensure_commande_mutable(commande)

    frontend_base_url = os.getenv("FRONTEND_BASE_URL", str(request.base_url).rstrip("/"))
    failed_url = f"{frontend_base_url}/payment?commandeId={payload.id_commande}&status=failed"

    # See build_pending_paiement: montant_chf/statut are never client-supplied.
    created = paiement_crud.create(db, build_pending_paiement(payload, commande))

    success_url = (
        f"{frontend_base_url}/payment?commandeId={payload.id_commande}"
        f"&paiementId={created.id_paiement}&status=success"
    )

    line_items, billing_address = build_postfinance_checkout_data(commande, lignes, user)

    pf_resp = create_postfinance_iframe_session(
        line_items=line_items,
        billing_address=billing_address,
        success_url=success_url,
        failed_url=failed_url,
        merchant_reference=str(created.id_paiement),
        shipping_address=billing_address,
    )

    transaction_id = pf_resp.get("transaction_id")
    if transaction_id:
        created.reference_externe = str(transaction_id)  # type: ignore[assignment]
    transaction = pf_resp.get("transaction") or {}
    transaction_status = transaction.get("state") or transaction.get("status")
    if transaction_status:
        created.statut = str(transaction_status)  # type: ignore[assignment]
    db.commit()
    db.refresh(created)

    return {
        "paiement": created,
        "transaction_id": transaction_id,
        "javascript_url": pf_resp.get("javascript_url"),
        "payment_methods": pf_resp.get("payment_methods") or [],
        "local_mode": bool(pf_resp.get("local_mode")),
        "error": pf_resp.get("error"),
    }


@router.post("/paiements/{id_paiement}/confirm-postfinance")
def confirm_paiement_postfinance(
    id_paiement: int,
    db: DbSession,
    current_user: CurrentUser,
):
    """Confirm a PostFinance transaction after iframe validation, before submit()."""
    obj = get_owned_paiement(db, id_paiement, int(current_user.id_utilisateur))
    if obj is None:
        raise HTTPException(status_code=404, detail="Paiement introuvable.")

    commande, lignes, user = load_commande_context(db, int(obj.id_commande), int(current_user.id_utilisateur))
    if commande is None:
        raise HTTPException(status_code=404, detail="Commande introuvable.")

    transaction_id = getattr(obj, "reference_externe", None)
    if not transaction_id:
        raise HTTPException(status_code=400, detail="Référence de transaction PostFinance manquante.")

    line_items, billing_address = build_postfinance_checkout_data(commande, lignes, user)

    current_tx = get_postfinance_transaction(str(transaction_id))
    version = int(current_tx.get("version") or 1)

    # No amount cross-check here. `confirm` runs *before* the iframe's own
    # submit() actually authorizes the transaction with PostFinance, and at
    # this stage PostFinance hasn't computed a real amount for it yet: both
    # completed_amount and authorization_amount come back as a bare 0 (not
    # None), which used to read as a genuine mismatch against any non-zero
    # commande total and produce a "montant ne correspond pas" 409 on every
    # single payment. The amount is only meaningful once authorization has
    # actually happened, which is exactly what poll_paiement_postfinance /
    # postfinance_webhook already verify (see _assert_amount_matches_commande
    # there) before finalizing.
    pf_resp = confirm_postfinance_transaction(
        transaction_id=str(transaction_id),
        version=version,
        merchant_reference=str(obj.id_paiement),
        line_items=line_items,
        billing_address=billing_address,
        shipping_address=billing_address,
    )

    already_finalized = is_postfinance_success_status(str(getattr(obj, "statut", "") or ""))
    if pf_resp.get("local"):
        obj.statut = "AUTHORIZED"  # type: ignore[assignment]
        obj.date_paiement = datetime.now(timezone.utc)  # type: ignore[assignment]
        db.commit()
        db.refresh(obj)
        if not already_finalized:
            _finalize_paid_order(db, int(obj.id_commande), source="confirm")  # type: ignore[arg-type]
        # The finalize commit above expires `obj` (expire_on_commit) — refresh
        # so its fields are populated when serialized in the response below,
        # rather than serializing as an empty object.
        db.refresh(obj)
    elif pf_resp.get("state") or pf_resp.get("status"):
        # This used to only persist `obj.statut` and never call
        # _finalize_paid_order, unlike the local/poll/webhook branches. A real
        # PostFinance confirm reporting a success state (e.g. AUTHORIZED) left
        # the payment looking done without ever decrementing stock or clearing
        # the cart reservation -- and since poll_paiement_postfinance returns
        # early once the status already reads as success, nothing downstream
        # ever finalized it either. The order was stuck forever: stock stayed
        # reserved, the book could never be withdrawn, and any retry hit the
        # amount-check against an already non-pending PostFinance transaction.
        new_status = str(pf_resp.get("state") or pf_resp.get("status"))
        is_success = is_postfinance_success_status(new_status)
        obj.statut = new_status  # type: ignore[assignment]
        if is_success:
            obj.date_paiement = datetime.now(timezone.utc)  # type: ignore[assignment]
        db.commit()
        db.refresh(obj)
        if is_success and not already_finalized:
            _finalize_paid_order(db, int(obj.id_commande), source="confirm")  # type: ignore[arg-type]
        db.refresh(obj)

    if pf_resp.get("error"):
        # The provider's own message is English; prefix it with something the
        # customer can act on rather than surfacing it raw.
        raise HTTPException(
            status_code=502,
            detail=(
                "Le paiement n’a pas pu être confirmé auprès de PostFinance. "
                f"Réessayez dans un instant. ({pf_resp.get('error')})"
            ),
        )

    return {"paiement": obj, "transaction": pf_resp}


@router.get("/paiements/{id_paiement}/poll-postfinance")
def poll_paiement_postfinance(id_paiement: int, db: DbSession, current_user: CurrentUser):
    """Poll PostFinance for the status of a payment (alternative to webhooks).

    This endpoint queries PostFinance using the stored `reference_externe` (link id)
    or falls back to searching by the local payment id. It updates the local payment
    status and finalizes the order if the payment is captured/paid.
    """
    obj = get_owned_paiement(db, id_paiement, int(current_user.id_utilisateur))
    if obj is None:
        raise HTTPException(status_code=404, detail="Paiement introuvable.")

    current_statut = str(getattr(obj, "statut", "") or "")
    # If already in a terminal success state, return without polling (avoids
    # local-mode overwriting AUTHORIZED/PAID back to PENDING).
    if is_postfinance_success_status(current_statut):
        return {"paiement": obj, "raw": {}}

    provider_id = getattr(obj, "reference_externe", None)
    pf_resp = get_postfinance_checkout_status(provider_id, str(obj.id_paiement))

    new_status = pf_resp.get("state") or pf_resp.get("status")
    if new_status and not is_postfinance_success_status(current_statut):
        is_success = is_postfinance_success_status(str(new_status))
        # Verify the amount BEFORE persisting a success status: raising here
        # leaves `obj.statut` untouched, so a mismatch doesn't get committed as
        # "already succeeded" and silently swallowed by the idempotency guard
        # on every later poll/webhook call (see C-1).
        if is_success:
            _assert_amount_matches_commande(db, int(obj.id_commande), pf_resp.get("amount"), source="poll")

        obj.statut = str(new_status)  # type: ignore[assignment]
        if is_success:
            obj.date_paiement = datetime.now(timezone.utc)  # type: ignore[assignment]
        db.commit()
        db.refresh(obj)

        if is_success:
            _finalize_paid_order(db, int(obj.id_commande), source="poll")  # type: ignore[arg-type]

    return {"paiement": obj, "raw": pf_resp}


@router.post("/paiements/webhook/postfinance")
async def postfinance_webhook(request: Request, db: DbSession):
    # PostFinance webhook signature verification
    sig_header = request.headers.get("x-signature") or request.headers.get("X-Signature")

    if not sig_header:
        raise HTTPException(status_code=403, detail="Signature du webhook manquante.")

    raw_body = await request.body()
    if not verify_postfinance_webhook_signature(raw_body, sig_header):
        raise HTTPException(status_code=403, detail="Signature du webhook invalide.")

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

    # Idempotency: PostFinance explicitly documents webhooks may be delivered
    # more than once. Without this guard, a replayed webhook would re-enter
    # finalize_commande and double-decrement real stock for an order that was
    # already finalized.
    already_finalized = is_postfinance_success_status(str(getattr(obj, "statut", "") or ""))

    new_status = parsed.get("status") or "UNKNOWN"
    is_new_success = not already_finalized and is_postfinance_success_status(str(new_status))

    # Verify the amount BEFORE persisting a success status (see C-1): if this
    # raises, `obj.statut` is left untouched instead of being committed as
    # "already succeeded", which would make the idempotency guard above
    # silently skip the check and finalize on every later webhook redelivery.
    if is_new_success:
        # The webhook payload itself may not carry a reliable amount field, so
        # re-fetch the transaction from PostFinance directly for the figure to
        # cross-check against, rather than trusting whatever (if anything) was
        # in the notification body.
        provider_tx = get_postfinance_transaction(str(pay_id or ref or obj.reference_externe))  # type: ignore[arg-type]
        _assert_amount_matches_commande(db, int(obj.id_commande), provider_tx.get("amount"), source="webhook")  # type: ignore[arg-type]

    obj.statut = new_status  # type: ignore
    obj.date_paiement = datetime.now(timezone.utc)  # type: ignore
    db.commit()
    db.refresh(obj)

    if is_new_success:
        _finalize_paid_order(db, int(obj.id_commande), source="webhook")  # type: ignore[arg-type]

    return {"ok": True}


@router.post("/paiements/webhook/local")
def local_payment_webhook(payload: dict, db: DbSession):
    """Development/test-only webhook simulator for local iframe payments.

    Fail-closed: only enabled when ENVIRONMENT is explicitly "development" or
    "test" (CI sets ENVIRONMENT=test, and the test suite itself relies on this
    endpoint to simulate PostFinance callbacks). Any other/missing/
    misconfigured value disables it, rather than requiring ENVIRONMENT to
    exactly equal "production" to disable it — an unauthenticated
    payment-forgery endpoint must never be reachable by a deployment mistake.
    """
    if os.getenv("ENVIRONMENT", "development").strip().lower() not in ("development", "test"):
        raise HTTPException(status_code=404, detail="Ressource introuvable.")

    ref = payload.get("reference") or payload.get("Metadata", {}).get("reference")
    pay_id = payload.get("Id") or payload.get("id")
    status_val = payload.get("Status") or payload.get("status") or "AUTHORIZED"

    obj = None
    if ref:
        obj = db.query(models.Paiement).filter(models.Paiement.reference_externe == str(ref)).first()
    if obj is None and pay_id:
        obj = db.query(models.Paiement).filter(models.Paiement.id_paiement == int(str(pay_id).replace("local-", ""))).first()
    if obj is None and ref:
        obj = db.query(models.Paiement).filter(models.Paiement.id_paiement == int(str(ref).replace("local-", ""))).first()
    if obj is None:
        return {"ok": False, "reason": "not_found"}

    already_finalized = is_postfinance_success_status(str(getattr(obj, "statut", "") or ""))

    obj.statut = str(status_val)  # type: ignore[assignment]
    obj.date_paiement = datetime.now(timezone.utc)  # type: ignore[assignment]
    db.commit()
    db.refresh(obj)

    if not already_finalized and is_postfinance_success_status(str(status_val)):
        _finalize_paid_order(db, int(obj.id_commande), source="local_webhook")  # type: ignore[arg-type]

    return {"ok": True}


@router.put("/paiements/{id_paiement}", response_model=PaiementRead)
def update_paiement(
    id_paiement: int,
    payload: PaiementUpdate,
    db: DbSession,
    _admin: AdminUser,
):
    """Admin-only. Payments are financial/audit records: a customer must never be
    able to edit or delete them (previously the owner could, via id_utilisateur
    scoping). Their status changes only through verified PostFinance callbacks, and
    any back-office correction is an admin action."""
    obj = db.query(models.Paiement).filter(models.Paiement.id_paiement == id_paiement).first()
    if obj is None:
        raise HTTPException(status_code=404, detail="Paiement introuvable.")
    # statut is intentionally not part of PaiementUpdate — a payment's status
    # may only change via a verified PostFinance callback (confirm/poll/webhook).
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        if hasattr(obj, k):
            setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/paiements/{id_paiement}", status_code=status.HTTP_204_NO_CONTENT)
def delete_paiement(id_paiement: int, db: DbSession, _admin: AdminUser):
    """Admin-only — see update_paiement. Deleting a payment record is a back-office
    action, never customer self-service."""
    obj = db.query(models.Paiement).filter(models.Paiement.id_paiement == id_paiement).first()
    if obj is None:
        raise HTTPException(status_code=404, detail="Paiement introuvable.")
    db.delete(obj)
    db.commit()
    return None
