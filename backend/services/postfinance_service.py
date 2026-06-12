from __future__ import annotations

import base64
import os
import time
from typing import Any, Dict, List, Optional

import httpx

from postfinancecheckout import Configuration, TransactionsService
from postfinancecheckout.models import AddressCreate, LineItemCreate, TransactionCreate, TransactionPending

POSTFINANCE_USER_ID = os.getenv("POSTFINANCE_USER_ID")
POSTFINANCE_AUTH_KEY = os.getenv("POSTFINANCE_AUTH_KEY")
POSTFINANCE_SPACE_ID = os.getenv("POSTFINANCE_SPACE_ID")
POSTFINANCE_WEBHOOK_PUBLIC_KEY_PEM = os.getenv("POSTFINANCE_WEBHOOK_PUBLIC_KEY_PEM")
POSTFINANCE_WEBHOOK_KEY_ID = os.getenv("POSTFINANCE_WEBHOOK_KEY_ID")

SUCCESS_STATUSES = frozenset(
    {"CAPTURED", "PAID", "COMPLETED", "AUTHORIZED", "FULFILL", "SUCCESSFUL", "FULFILLED"}
)


def _credentials_configured() -> bool:
    return bool(POSTFINANCE_USER_ID and POSTFINANCE_AUTH_KEY and POSTFINANCE_SPACE_ID)


def _transactions_service() -> TransactionsService:
    config = Configuration(
        user_id=str(POSTFINANCE_USER_ID),
        authentication_key=str(POSTFINANCE_AUTH_KEY),
    )
    return TransactionsService(config)


def _space_id() -> int:
    return int(str(POSTFINANCE_SPACE_ID))


def _state_str(state: Any) -> Optional[str]:
    if state is None:
        return None
    return getattr(state, "value", None) or str(state)


def build_postfinance_line_items(
    lignes: List[Any],
    frais_port_chf: float,
    shipping_label: str,
    commande_id: int,
) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for ligne in lignes:
        article = getattr(ligne, "article", None)
        sku = getattr(article, "sku", None) if article is not None else None
        titre = getattr(article, "titre", None) if article is not None else None
        qty = int(getattr(ligne, "quantite", 1) or 1)
        unit_price = float(getattr(ligne, "prix_unitaire_chf", 0) or 0)
        ligne_id = getattr(ligne, "id_ligne_commande", 0)
        article_id = getattr(ligne, "id_article", 0)
        items.append(
            {
                "uniqueId": f"ligne-{ligne_id}",
                "sku": sku or f"article-{article_id}",
                "name": (titre or f"Article {article_id}")[:150],
                "quantity": qty,
                "amountIncludingTax": round(unit_price * qty, 2),
                "type": "PRODUCT",
                "shippingRequired": True,
            }
        )

    if frais_port_chf > 0:
        items.append(
            {
                "uniqueId": f"shipping-{commande_id}",
                "sku": f"shipping-{commande_id}",
                "name": shipping_label[:150],
                "quantity": 1,
                "amountIncludingTax": round(frais_port_chf, 2),
                "type": "SHIPPING",
                "shippingRequired": False,
            }
        )
    return items


def build_postfinance_address(user: Any) -> Dict[str, str]:
    country = getattr(user, "billing_country", None) or "CH"
    if len(country) > 2:
        country = "CH"
    return {
        "givenName": getattr(user, "prenom", "") or "",
        "familyName": getattr(user, "nom", "") or "",
        "emailAddress": getattr(user, "email", "") or "",
        "street": getattr(user, "billing_address_line1", "") or "",
        "city": getattr(user, "billing_city", "") or "",
        "postcode": getattr(user, "billing_postal_code", "") or "",
        "country": country,
        "phoneNumber": getattr(user, "billing_phone", "") or "",
    }


def _line_items_to_models(line_items: List[Dict[str, Any]]) -> List[LineItemCreate]:
    return [LineItemCreate.from_dict(item) for item in line_items]


def _address_to_model(address: Dict[str, str]) -> AddressCreate:
    return AddressCreate.from_dict(address)


def create_postfinance_transaction(
    line_items: List[Dict[str, Any]],
    billing_address: Dict[str, str],
    success_url: str,
    failed_url: str,
    merchant_reference: Optional[str] = None,
    shipping_address: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """Create a PostFinance transaction for iframe checkout."""
    if not _credentials_configured():
        return {
            "id": f"local-{merchant_reference or int(time.time())}",
            "status": "PENDING",
            "state": "PENDING",
            "version": 1,
            "local": True,
        }

    try:
        tx_create = TransactionCreate.from_dict(
            {
                "currency": "CHF",
                "language": "fr-CH",
                "lineItems": line_items,
                "billingAddress": billing_address,
                "shippingAddress": shipping_address or billing_address,
                "successUrl": success_url,
                "failedUrl": failed_url,
                "merchantReference": merchant_reference,
            }
        )
        tx = _transactions_service().post_payment_transactions(
            space=_space_id(), transaction_create=tx_create
        )
        status = _state_str(tx.state)
        return {
            "id": tx.id,
            "status": status,
            "state": status,
            "version": tx.version,
        }
    except Exception as exc:
        return {"id": None, "status": "ERROR", "state": "ERROR", "error": str(exc)}


def get_postfinance_payment_methods(transaction_id: str) -> Dict[str, Any]:
    """Fetch payment method configurations available for iframe integration."""
    if not _credentials_configured():
        return {
            "data": [
                {
                    "id": 0,
                    "name": "Simulation locale",
                    "resolvedTitle": {"fr-CH": "Simulation locale"},
                    "resolvedImageUrl": None,
                }
            ],
            "local": True,
        }

    try:
        resp = _transactions_service().get_payment_transactions_id_payment_method_configurations(
            id=int(transaction_id), space=_space_id(), integration_mode="IFRAME"
        )
        methods = [m.to_dict() for m in (resp.data or [])]
        return {"data": methods}
    except Exception as exc:
        return {"data": [], "error": str(exc)}


def get_postfinance_javascript_url(transaction_id: str) -> Dict[str, Any]:
    """Retrieve the JavaScript URL required to embed the iframe checkout handler."""
    if not _credentials_configured():
        return {"javascript_url": None, "local": True}

    try:
        url = _transactions_service().get_payment_transactions_id_iframe_javascript_url(
            id=int(transaction_id), space=_space_id()
        )
        return {"javascript_url": url or None}
    except Exception as exc:
        return {"javascript_url": None, "error": str(exc)}


def get_postfinance_transaction(transaction_id: str) -> Dict[str, Any]:
    """Read a transaction by provider id."""
    if not _credentials_configured():
        return {
            "id": transaction_id,
            "status": "PENDING",
            "state": "PENDING",
            "version": 1,
            "local": True,
        }

    try:
        tx = _transactions_service().get_payment_transactions_id(
            id=int(transaction_id), space=_space_id()
        )
        status = _state_str(tx.state)
        return {
            "id": tx.id or transaction_id,
            "status": status,
            "state": status,
            "version": tx.version,
            "merchantReference": tx.merchant_reference,
        }
    except Exception as exc:
        return {"id": transaction_id, "status": None, "state": None, "error": str(exc)}


def confirm_postfinance_transaction(
    transaction_id: str,
    version: int,
    merchant_reference: str,
    line_items: List[Dict[str, Any]],
    billing_address: Dict[str, str],
    shipping_address: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """Confirm a pending transaction before iframe submit."""
    if not _credentials_configured():
        return {
            "id": transaction_id,
            "status": "CONFIRMED",
            "state": "CONFIRMED",
            "version": version,
            "local": True,
        }

    try:
        pending = TransactionPending.from_dict(
            {
                "version": version,
                "merchantReference": merchant_reference,
                "lineItems": line_items,
                "billingAddress": billing_address,
                "shippingAddress": shipping_address or billing_address,
            }
        )
        tx = _transactions_service().post_payment_transactions_id_confirm(
            id=int(transaction_id), space=_space_id(), transaction_pending=pending
        )
        status = _state_str(tx.state)
        return {
            "id": tx.id or transaction_id,
            "status": status,
            "state": status,
            "version": tx.version,
        }
    except Exception as exc:
        return {"id": transaction_id, "status": "ERROR", "state": "ERROR", "error": str(exc)}


def create_postfinance_iframe_session(
    line_items: List[Dict[str, Any]],
    billing_address: Dict[str, str],
    success_url: str,
    failed_url: str,
    merchant_reference: Optional[str] = None,
    shipping_address: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """Create a transaction and fetch iframe assets (payment methods + JavaScript URL)."""
    transaction = create_postfinance_transaction(
        line_items=line_items,
        billing_address=billing_address,
        success_url=success_url,
        failed_url=failed_url,
        merchant_reference=merchant_reference,
        shipping_address=shipping_address,
    )

    transaction_id = transaction.get("id")
    if not transaction_id:
        return {
            "transaction_id": None,
            "transaction": transaction,
            "payment_methods": [],
            "javascript_url": None,
            "error": transaction.get("error") or "Could not create PostFinance transaction",
            "local_mode": not _credentials_configured(),
        }

    payment_methods_resp = get_postfinance_payment_methods(str(transaction_id))
    javascript_resp = get_postfinance_javascript_url(str(transaction_id))

    return {
        "transaction_id": str(transaction_id),
        "transaction": transaction,
        "payment_methods": payment_methods_resp.get("data") or [],
        "javascript_url": javascript_resp.get("javascript_url"),
        "local_mode": bool(transaction.get("local")),
        "error": transaction.get("error") or javascript_resp.get("error") or payment_methods_resp.get("error"),
    }


def get_postfinance_checkout_status(
    link_id: Optional[str] = None,
    external_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Query PostFinance for a transaction status (iframe / transaction API)."""
    if link_id:
        return get_postfinance_transaction(str(link_id))

    if external_id:
        return get_postfinance_transaction(str(external_id))

    return {"id": None, "status": None, "state": None, "raw": None}


def verify_postfinance_webhook_signature(raw_body: bytes, signature_header: str) -> bool:
    """Verify a PostFinance webhook signature using the SDK's built-in verifier.
    The SDK fetches the public key automatically from PostFinance using the keyId
    embedded in the x-signature header — no env vars needed."""
    try:
        from postfinancecheckout.configuration import Configuration
        from postfinancecheckout.service.webhook_encryption_keys_service import WebhookEncryptionKeysService
        config = Configuration(
            user_id=str(POSTFINANCE_USER_ID or ""),
            authentication_key=str(POSTFINANCE_AUTH_KEY or ""),
        )
        svc = WebhookEncryptionKeysService(config)
        return bool(svc.is_content_valid(signature_header, raw_body.decode("utf-8")))
    except Exception:
        return False


def parse_postfinance_webhook(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Parse a PostFinance webhook payload into a standard dict."""
    entity_id = payload.get("id") or payload.get("transactionId") or payload.get("checkoutId")
    status = payload.get("state") or payload.get("status")

    merchant_order_id = (
        payload.get("merchantReference")
        or payload.get("merchantOrderId")
        or payload.get("merchantOrderID")
        or payload.get("externalId")
        or payload.get("externalid")
        or payload.get("externalID")
    )

    if isinstance(merchant_order_id, dict):
        merchant_order_id = merchant_order_id.get("id") or merchant_order_id.get("externalId")

    if not merchant_order_id and isinstance(payload.get("entity"), dict):
        entity = payload["entity"]
        merchant_order_id = entity.get("merchantReference") or entity.get("merchantOrderId")
        if not entity_id:
            entity_id = entity.get("id")
        if not status:
            status = entity.get("state") or entity.get("status")

    if not merchant_order_id and isinstance(payload.get("transactions"), list) and payload["transactions"]:
        first = payload["transactions"][0]
        merchant_order_id = first.get("merchantReference") or first.get("merchantOrderId") or first.get("externalId")
        if not entity_id:
            entity_id = first.get("id")
        if not status:
            status = first.get("state") or first.get("status")

    return {
        "id": entity_id,
        "status": status,
        "reference": merchant_order_id,
        "raw": payload,
    }


def is_postfinance_success_status(status: Optional[str]) -> bool:
    if not status:
        return False
    return str(status).upper() in SUCCESS_STATUSES
