from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from typing import Any, Dict, Optional

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


def _get_auth_header(request_path: str = "/api/v2.0/payment/links", request_method: str = "POST") -> Dict[str, str]:
    """Build a JWT Bearer auth header from the application user credentials.

    The PostFinance signing payload must include the request path and method used for
    the request. This function accepts them so the same signing logic can be used for
    POST (create) and GET (status) requests.
    """
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


def create_postfinance_checkout(
    amount_chf: float,
    reference: str,
    return_url: str,
    cancel_url: str,
    description: str,
    customer_email: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a PostFinance payment link and return its public URL.
    
    Uses JWT bearer authentication with the application user ID and auth key.
    If credentials are not configured, returns a local simulated URL for testing.
    """
    amount = int(round(amount_chf * 100))  # cents

    if not POSTFINANCE_USER_ID or not POSTFINANCE_AUTH_KEY or not POSTFINANCE_SPACE_ID:
        # Development fallback: return a local testing URL
        return {
            "id": f"local-{reference}",
            "status": "CREATED",
            "redirect_url": f"/orders/paiements/local/redirect/{reference}",
        }

    from urllib.parse import urlparse

    frontend_origin = f"{urlparse(return_url).scheme}://{urlparse(return_url).netloc}" if return_url else "http://localhost:3000"
    payload = {
        "name": description,
        "externalId": reference,
        "merchantOrderId": reference,
        "currency": "CHF",
        "allowedRedirectionDomains": [frontend_origin],
        "language": "fr-CH",
        "successUrl": return_url,
        "failedUrl": cancel_url,
        "lineItems": [
            {
                "uniqueId": reference,
                "name": description,
                "amountIncludingTax": round(amount_chf, 2),
                "quantity": 1,
                "type": "PRODUCT",
            }
        ],
    }

    if customer_email:
        payload["customerEmailAddress"] = customer_email

    headers = _get_auth_header()
    headers["Content-Type"] = "application/json"
    # PostFinance may accept different header capitalizations; set common names
    headers["space"] = str(POSTFINANCE_SPACE_ID)
    headers["X-Space-Id"] = str(POSTFINANCE_SPACE_ID)

    url = POSTFINANCE_BASE.rstrip("/") + "/v2.0/payment/links"

    try:
        with httpx.Client(timeout=10.0) as client:
            r = client.post(url, json=payload, headers=headers)
            r.raise_for_status()
            data = r.json()
            payment_link_id = data.get("id") or data.get("ID")
            redirect_url = data.get("url") or data.get("URL") or data.get("linkUrl")
            return {
                "id": payment_link_id or reference,
                "status": "CREATED",
                "redirect_url": redirect_url,
                "raw": data,
            }
    except Exception as e:
        return {"id": reference, "status": "ERROR", "redirect_url": None, "error": str(e)}


def parse_postfinance_signature_header(signature_header: str) -> Dict[str, str]:
    parts: Dict[str, str] = {}
    for chunk in signature_header.split(","):
        if "=" not in chunk:
            continue
        key, value = chunk.split("=", 1)
        k = key.strip()
        # signature header values may be quoted; remove surrounding quotes
        v = value.strip().strip('"').strip("'")
        parts[k] = v
    return parts


def verify_postfinance_webhook_signature(raw_body: bytes, signature_header: str) -> bool:
    """Verify a PostFinance webhook signature using the documented x-signature header."""
    if not POSTFINANCE_WEBHOOK_PUBLIC_KEY_PEM:
        return False

    parts = parse_postfinance_signature_header(signature_header)
    if parts.get("algorithm") != "SHA256withECDSA":
        return False
    if POSTFINANCE_WEBHOOK_KEY_ID and parts.get("keyId") and parts.get("keyId") != POSTFINANCE_WEBHOOK_KEY_ID:
        return False

    signature_value = parts.get("signature")
    if not signature_value:
        return False

    try:
        public_key = serialization.load_pem_public_key(POSTFINANCE_WEBHOOK_PUBLIC_KEY_PEM.encode("utf-8"))
        if not isinstance(public_key, ec.EllipticCurvePublicKey):
            return False
        public_key.verify(base64.b64decode(signature_value), raw_body, ec.ECDSA(hashes.SHA256()))
        return True
    except (ValueError, InvalidSignature, TypeError):
        return False


def parse_postfinance_webhook(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Parse a PostFinance webhook payload into a standard dict."""
    # Tolerant parsing for different PostFinance webhook shapes
    checkout_id = payload.get("id") or payload.get("checkoutId")
    status = payload.get("status") or payload.get("state")

    # Prefer merchantOrderId, but fallback to externalId or nested values
    merchant_order_id = (
        payload.get("merchantOrderId")
        or payload.get("merchantOrderID")
        or payload.get("externalId")
        or payload.get("externalid")
        or payload.get("externalID")
    )

    # If nested object, try to extract id or externalId
    if isinstance(merchant_order_id, dict):
        merchant_order_id = merchant_order_id.get("id") or merchant_order_id.get("externalId")

    # Some webhook payloads include transactions or checkout details
    if not merchant_order_id:
        if isinstance(payload.get("transactions"), list) and len(payload.get("transactions")) > 0:
            t0 = payload["transactions"][0]
            merchant_order_id = t0.get("merchantOrderId") or t0.get("externalId")

    return {
        "id": checkout_id,
        "status": status,
        "reference": merchant_order_id,
        "raw": payload,
    }


def get_postfinance_checkout_status(link_id: Optional[str] = None, external_id: Optional[str] = None) -> Dict[str, Any]:
    """Query PostFinance for a payment link / checkout status without relying on webhooks.

    Tries to GET the link by `link_id` (provider id) first, then falls back to searching
    by `external_id` (externalId/merchantOrderId). Returns a dict with `id`, `status`, and
    the raw provider response under `raw`. In development (no credentials) returns a
    simulated response.
    """
    if not POSTFINANCE_USER_ID or not POSTFINANCE_AUTH_KEY or not POSTFINANCE_SPACE_ID:
        # Development fallback
        return {
            "id": link_id or f"local-{external_id}",
            "status": "CREATED",
            "raw": {"local": True},
        }

    # Helper to add common headers
    def _common_headers(path: str, method: str) -> Dict[str, str]:
        h = _get_auth_header(path, method)
        h["Accept"] = "application/json"
        h["space"] = str(POSTFINANCE_SPACE_ID)
        h["X-Space-Id"] = str(POSTFINANCE_SPACE_ID)
        return h

    base = POSTFINANCE_BASE.rstrip("/")

    # Try lookup by link id
    if link_id:
        url = f"{base}/v2.0/payment/links/{link_id}"
        try:
            headers = _common_headers(f"/api/v2.0/payment/links/{link_id}", "GET")
            with httpx.Client(timeout=10.0) as client:
                r = client.get(url, headers=headers)
                r.raise_for_status()
                data = r.json()
                status = data.get("status") or data.get("state")
                return {"id": data.get("id") or link_id, "status": status, "raw": data}
        except Exception:
            # fall through to try external id
            pass

    # Try searching by external id
    if external_id:
        url = f"{base}/v2.0/payment/links"
        try:
            headers = _common_headers("/api/v2.0/payment/links", "GET")
            params = {"externalId": external_id}
            with httpx.Client(timeout=10.0) as client:
                r = client.get(url, headers=headers, params=params)
                r.raise_for_status()
                data = r.json()
                # Extract list-like responses
                items = []
                if isinstance(data, dict):
                    for k in ("data", "items", "rows", "result"):
                        if isinstance(data.get(k), list):
                            items = data.get(k)
                            break
                    if not items and (data.get("id") or data.get("ID")):
                        items = [data]
                elif isinstance(data, list):
                    items = data

                if items:
                    first = items[0]
                    status = first.get("status") or first.get("state")
                    return {"id": first.get("id") or external_id, "status": status, "raw": first}
        except Exception as e:
            return {"error": str(e)}

    return {"id": None, "status": None, "raw": None}
