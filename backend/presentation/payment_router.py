from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

logger = logging.getLogger("caribooks.orders")

from infrastructure import models
from infrastructure.crud_base import CrudBase
from presentation.deps import get_current_user, get_db, require_admin
from presentation.schemas import PaiementCreate, PaiementRead, PaiementUpdate
from services.order_service import (
    build_pending_paiement,
    finalize_commande,
    get_commande_owned,
    load_commande_context,
)
from services.postfinance_service import (
    build_postfinance_checkout_data,
    confirm_postfinance_transaction,
    create_postfinance_iframe_session,
    get_postfinance_checkout_status,
    get_postfinance_transaction,
    is_postfinance_success_status,
    parse_postfinance_webhook,
    verify_postfinance_webhook_signature,
)

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
    commande = get_commande_owned(db, payload.id_commande, int(current_user.id_utilisateur))
    if commande is None:
        raise HTTPException(status_code=404, detail="Commande not found")
    # See build_pending_paiement: a payment always starts PENDING with the
    # commande's own server-computed total, never a client-supplied one.
    return paiement_crud.create(db, build_pending_paiement(payload, commande))


@router.post("/paiements/postfinance", status_code=status.HTTP_201_CREATED)
def create_paiement_postfinance(
    payload: PaiementCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Create a local paiement and initialize a PostFinance iframe checkout session."""
    commande, lignes, user = load_commande_context(db, payload.id_commande, int(current_user.id_utilisateur))
    if commande is None:
        raise HTTPException(status_code=404, detail="Commande not found")

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
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Confirm a PostFinance transaction after iframe validation, before submit()."""
    obj = (
        db.query(models.Paiement)
        .join(models.Commande, models.Paiement.id_commande == models.Commande.id_commande)
        .filter(
            models.Paiement.id_paiement == id_paiement,
            models.Commande.id_utilisateur == current_user.id_utilisateur,
        )
        .first()
    )
    if obj is None:
        raise HTTPException(status_code=404, detail="Paiement not found")

    commande, lignes, user = load_commande_context(db, int(obj.id_commande), int(current_user.id_utilisateur))
    if commande is None:
        raise HTTPException(status_code=404, detail="Commande not found")

    transaction_id = getattr(obj, "reference_externe", None)
    if not transaction_id:
        raise HTTPException(status_code=400, detail="Missing PostFinance transaction reference")

    line_items, billing_address = build_postfinance_checkout_data(commande, lignes, user)

    current_tx = get_postfinance_transaction(str(transaction_id))
    version = int(current_tx.get("version") or 1)

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
        obj.statut = str(pf_resp.get("state") or pf_resp.get("status"))  # type: ignore[assignment]
        db.commit()
        db.refresh(obj)

    if pf_resp.get("error"):
        raise HTTPException(status_code=502, detail=str(pf_resp.get("error")))

    return {"paiement": obj, "transaction": pf_resp}


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

    current_statut = str(getattr(obj, "statut", "") or "")
    # If already in a terminal success state, return without polling (avoids
    # local-mode overwriting AUTHORIZED/PAID back to PENDING).
    if is_postfinance_success_status(current_statut):
        return {"paiement": obj, "raw": {}}

    provider_id = getattr(obj, "reference_externe", None)
    pf_resp = get_postfinance_checkout_status(provider_id, str(obj.id_paiement))

    new_status = pf_resp.get("state") or pf_resp.get("status")
    if new_status and not is_postfinance_success_status(current_statut):
        obj.statut = str(new_status)  # type: ignore[assignment]
        if is_postfinance_success_status(str(new_status)):
            obj.date_paiement = datetime.now(timezone.utc)  # type: ignore[assignment]
        db.commit()
        db.refresh(obj)

        if is_postfinance_success_status(str(new_status)):
            _finalize_paid_order(db, int(obj.id_commande), source="poll")  # type: ignore[arg-type]

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

    # Idempotency: PostFinance explicitly documents webhooks may be delivered
    # more than once. Without this guard, a replayed webhook would re-enter
    # finalize_commande and double-decrement real stock for an order that was
    # already finalized.
    already_finalized = is_postfinance_success_status(str(getattr(obj, "statut", "") or ""))

    new_status = parsed.get("status") or "UNKNOWN"
    obj.statut = new_status  # type: ignore
    obj.date_paiement = datetime.now(timezone.utc)  # type: ignore
    db.commit()
    db.refresh(obj)

    if not already_finalized and is_postfinance_success_status(str(new_status)):
        _finalize_paid_order(db, int(obj.id_commande), source="webhook")  # type: ignore[arg-type]

    return {"ok": True}


@router.post("/paiements/webhook/local")
def local_payment_webhook(payload: dict, db: Session = Depends(get_db)):
    """Development/test-only webhook simulator for local iframe payments.

    Fail-closed: only enabled when ENVIRONMENT is explicitly "development" or
    "test" (CI sets ENVIRONMENT=test, and the test suite itself relies on this
    endpoint to simulate PostFinance callbacks). Any other/missing/
    misconfigured value disables it, rather than requiring ENVIRONMENT to
    exactly equal "production" to disable it — an unauthenticated
    payment-forgery endpoint must never be reachable by a deployment mistake.
    """
    if os.getenv("ENVIRONMENT", "development").strip().lower() not in ("development", "test"):
        raise HTTPException(status_code=404, detail="Not found")

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
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):
    """Admin-only. Payments are financial/audit records: a customer must never be
    able to edit or delete them (previously the owner could, via id_utilisateur
    scoping). Their status changes only through verified PostFinance callbacks, and
    any back-office correction is an admin action."""
    obj = db.query(models.Paiement).filter(models.Paiement.id_paiement == id_paiement).first()
    if obj is None:
        raise HTTPException(status_code=404, detail="Paiement not found")
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
def delete_paiement(id_paiement: int, db: Session = Depends(get_db), _admin=Depends(require_admin)):
    """Admin-only — see update_paiement. Deleting a payment record is a back-office
    action, never customer self-service."""
    obj = db.query(models.Paiement).filter(models.Paiement.id_paiement == id_paiement).first()
    if obj is None:
        raise HTTPException(status_code=404, detail="Paiement not found")
    db.delete(obj)
    db.commit()
    return None
