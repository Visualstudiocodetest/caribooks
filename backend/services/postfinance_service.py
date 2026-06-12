from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from typing import Any, Dict, List, Optional

import httpx
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec

POSTFINANCE_USER_ID = os.getenv("POSTFINANCE_USER_ID")
POSTFINANCE_AUTH_KEY = os.getenv("POSTFINANCE_AUTH_KEY")
POSTFINANCE_BASE = os.getenv("POSTFINANCE_BASE_URL", "https://checkout.postfinance.ch/api")
POSTFINANCE_SPACE_ID = os.getenv("POSTFINANCE_SPACE_ID")
POSTFINANCE_WEBHOOK_PUBLIC_KEY_PEM = os.getenv("POSTFINANCE_WEBHOOK_PUBLIC_KEY_PEM")
POSTFINANCE_WEBHOOK_KEY_ID = os.getenv("POSTFINANCE_WEBHOOK_KEY_ID")

SUCCESS_STATUSES = frozenset(
    {"CAPTURED", "PAID", "COMPLETED", "AUTHORIZED", "FULFILL", "SUCCESSFUL", "FULFILLED"}
)


def _credentials_configured() -> bool:
    return bool(POSTFINANCE_USER_ID and POSTFINANCE_AUTH_KEY and POSTFINANCE_SPACE_ID)


def _get_auth_header(request_path: str, request_method: str = "POST") -> Dict[str, str]:
    """Build a JWT Bearer auth header from the application user credentials."""
    if not POSTFINANCE_USER_ID or not POSTFINANCE_AUTH_KEY:
        return {}

    try:
        signing_key = base64.b64decode(POSTFINANCE_AUTH_KEY)
    except Exception:
        signing_key = POSTFINANCE_AUTH_KEY.encode("utf-8")

    payload = {
        "sub": str(POSTFINANCE_USER_ID),
        "iat": int(time.time()),
        "requestPath": request_path,
        "requestMethod": request_method,
    }
    headers = {"alg": "HS256", "typ": "JWT", "ver": 1}
    header_json = json.dumps(headers, separators=(",", ":")).encode("utf-8")
    payload_json = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    header_segment = base64.urlsafe_b64encode(header_json).rstrip(b"=")
    payload_segment = base64.urlsafe_b64encode(payload_json).rstrip(b"=")
    signing_input = header_segment + b"." + payload_segment
    signature = hmac.new(signing_key, signing_input, hashlib.sha256).digest()
    signature_segment = base64.urlsafe_b64encode(signature).rstrip(b"=")
    token = b".".join([header_segment, payload_segment, signature_segment]).decode("utf-8")
    return {"Authorization": f"Bearer {token}"}


def _signed_request(path_suffix: str, method: str, extra_params: Optional[Dict[str, str]] = None) -> tuple[str, Dict[str, str]]:
    """Return (url, headers) for a PostFinance v2.0 API call.

    spaceId must appear as a query param AND be included in the JWT requestPath
    for authentication to succeed. Extra params (e.g. integrationMode) are
    appended to the URL but not to the signed requestPath.
    """
    from urllib.parse import urlencode
    # Path signed in JWT always includes spaceId
    signed_path = f"/api/v2.0{path_suffix}?spaceId={POSTFINANCE_SPACE_ID}"
    # Full URL may have additional query params
    if extra_params:
        full_url = f"https://checkout.postfinance.ch{signed_path}&{urlencode(extra_params)}"
    else:
        full_url = f"https://checkout.postfinance.ch{signed_path}"
    headers = _get_auth_header(signed_path, method)
    headers["Content-Type"] = "application/json"
    headers["Accept"] = "application/json"
    return full_url, headers


def _decode_string_response(data: Any) -> Optional[str]:
    if isinstance(data, str):
        return data
    if isinstance(data, dict):
        for key in ("url", "URL", "value", "javascriptUrl"):
            value = data.get(key)
            if isinstance(value, str):
                return value
    return None


def _extract_list_payload(data: Any) -> List[Dict[str, Any]]:
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("data", "items", "rows", "result"):
            value = data.get(key)
            if isinstance(value, list):
                return value
        if data.get("id"):
            return [data]
    return []


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

    payload: Dict[str, Any] = {
        "currency": "CHF",
        "language": "fr-CH",
        "lineItems": line_items,
        "billingAddress": billing_address,
        "shippingAddress": shipping_address or billing_address,
        "successUrl": success_url,
        "failedUrl": failed_url,
        "autoConfirmationEnabled": True,
    }
    if merchant_reference:
        payload["merchantReference"] = merchant_reference

    url, headers = _signed_request("/payment/transactions", "POST")

    try:
        with httpx.Client(timeout=15.0) as client:
            response = client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            transaction_id = data.get("id")
            status = data.get("state") or data.get("status")
            return {
                "id": transaction_id,
                "status": status,
                "state": status,
                "version": data.get("version"),
                "raw": data,
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

    url, headers = _signed_request(
        f"/payment/transactions/{transaction_id}/payment-method-configurations",
        "GET",
        {"integrationMode": "IFRAME"},
    )

    try:
        with httpx.Client(timeout=15.0) as client:
            response = client.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            methods = _extract_list_payload(data)
            return {"data": methods, "raw": data}
    except Exception as exc:
        return {"data": [], "error": str(exc)}


def get_postfinance_javascript_url(transaction_id: str) -> Dict[str, Any]:
    """Retrieve the JavaScript URL required to embed the iframe checkout handler."""
    if not _credentials_configured():
        return {"javascript_url": None, "local": True}

    url, headers = _signed_request(
        f"/payment/transactions/{transaction_id}/iframe-javascript-url",
        "GET",
    )
    # This endpoint returns text/plain (a bare URL string), not JSON.
    headers["Accept"] = "text/plain, application/json"

    try:
        with httpx.Client(timeout=15.0) as client:
            response = client.get(url, headers=headers)
            response.raise_for_status()
            content_type = response.headers.get("content-type", "")
            if "application/json" in content_type:
                javascript_url = _decode_string_response(response.json())
            else:
                javascript_url = response.text.strip() or None
            return {"javascript_url": javascript_url}
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

    url, headers = _signed_request(f"/payment/transactions/{transaction_id}", "GET")

    try:
        with httpx.Client(timeout=15.0) as client:
            response = client.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            status = data.get("state") or data.get("status")
            return {
                "id": data.get("id") or transaction_id,
                "status": status,
                "state": status,
                "version": data.get("version"),
                "merchantReference": data.get("merchantReference"),
                "raw": data,
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

    payload: Dict[str, Any] = {
        "id": int(transaction_id),
        "version": version,
        "currency": "CHF",
        "language": "fr-CH",
        "merchantReference": merchant_reference,
        "lineItems": line_items,
        "billingAddress": billing_address,
        "shippingAddress": shipping_address or billing_address,
    }

    url, headers = _signed_request(f"/payment/transactions/{transaction_id}/confirm", "POST")

    try:
        with httpx.Client(timeout=15.0) as client:
            response = client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            status = data.get("state") or data.get("status")
            return {
                "id": data.get("id") or transaction_id,
                "status": status,
                "state": status,
                "version": data.get("version"),
                "raw": data,
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


def parse_postfinance_signature_header(signature_header: str) -> Dict[str, str]:
    parts: Dict[str, str] = {}
    for chunk in signature_header.split(","):
        if "=" not in chunk:
            continue
        key, value = chunk.split("=", 1)
        parts[key.strip()] = value.strip().strip('"').strip("'")
    return parts


# In-process cache: keyId -> PEM string (avoids repeated HTTP calls per restart)
_key_pem_cache: Dict[str, str] = {}


def _fetch_encryption_key_pem(key_id: str) -> Optional[str]:
    """Fetch the PEM public key from PostFinance's public API using a keyId.
    No authentication required — the endpoint is publicly accessible."""
    cached = _key_pem_cache.get(key_id)
    if cached:
        return cached
    try:
        url = f"https://checkout.postfinance.ch/api/v2.0/webhooks/encryption-keys/{key_id}"
        r = httpx.get(url, timeout=10)
        r.raise_for_status()
        pem = r.text.strip()
        if pem:
            _key_pem_cache[key_id] = pem
            return pem
    except Exception:
        pass
    return None


def verify_postfinance_webhook_signature(raw_body: bytes, signature_header: str) -> bool:
    """Verify a PostFinance webhook signature using the documented x-signature header.
    The public key is resolved from env (POSTFINANCE_WEBHOOK_PUBLIC_KEY_PEM) or fetched
    automatically from PostFinance's public API using the keyId in the header."""
    parts = parse_postfinance_signature_header(signature_header)
    if parts.get("algorithm") != "SHA256withECDSA":
        return False

    signature_value = parts.get("signature")
    if not signature_value:
        return False

    key_id = parts.get("keyId", "")

    # Resolve PEM: prefer env var, fall back to live API fetch
    pem: Optional[str] = None
    if POSTFINANCE_WEBHOOK_PUBLIC_KEY_PEM:
        if not POSTFINANCE_WEBHOOK_KEY_ID or key_id == POSTFINANCE_WEBHOOK_KEY_ID:
            pem = POSTFINANCE_WEBHOOK_PUBLIC_KEY_PEM.replace("\\n", "\n")
    if pem is None and key_id:
        pem = _fetch_encryption_key_pem(key_id)

    if not pem:
        return False

    try:
        public_key = serialization.load_pem_public_key(pem.encode("utf-8"))
        if not isinstance(public_key, ec.EllipticCurvePublicKey):
            return False
        public_key.verify(base64.b64decode(signature_value), raw_body, ec.ECDSA(hashes.SHA256()))
        return True
    except (ValueError, InvalidSignature, TypeError):
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
