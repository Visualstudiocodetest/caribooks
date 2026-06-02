from __future__ import annotations

import os
from typing import Dict, Any

import httpx

PAYMENT_PROVIDER_API_KEY = os.getenv("PAYMENT_PROVIDER_API_KEY")
PAYMENT_PROVIDER_BASE = os.getenv("PAYMENT_PROVIDER_BASE", "")


def create_external_payment(amount_chf: float, reference: str, return_url: str, cancel_url: str, description: str) -> Dict[str, Any]:
    """Create a payment with an external provider and return provider response including a redirect URL.

    If `PAYMENT_PROVIDER_API_KEY` or `PAYMENT_PROVIDER_BASE` is not configured, returns a local simulated URL for testing.
    """
    amount = int(round(amount_chf * 100))  # cents

    if not PAYMENT_PROVIDER_API_KEY or not PAYMENT_PROVIDER_BASE:
        # Development fallback: return a local testing URL
        return {"id": f"local-{reference}", "status": "CREATED", "redirect_url": f"/orders/paiements/local/redirect/{reference}"}

    payload = {
        "Amount": amount,
        "Currency": "CHF",
        "Description": description,
        "RedirectUrl": return_url,
        "CancelUrl": cancel_url,
        "Metadata": {"reference": reference},
    }

    headers = {"Authorization": f"Bearer {PAYMENT_PROVIDER_API_KEY}", "Content-Type": "application/json"}
    url = PAYMENT_PROVIDER_BASE.rstrip("/") + "/Payment"

    try:
        with httpx.Client(timeout=10.0) as client:
            r = client.post(url, json=payload, headers=headers)
            r.raise_for_status()
            data = r.json()
            # Attempt to extract a redirect URL from provider response
            redirect = None
            if isinstance(data, dict):
                redirect = data.get("Url") or data.get("url")
                if not redirect:
                    for k in ("Payment", "payment", "data"):
                        sub = data.get(k)
                        if isinstance(sub, dict):
                            redirect = sub.get("Url") or sub.get("url") or redirect
            return {"id": data.get("Id") or data.get("id") or reference, "status": "CREATED", "redirect_url": redirect, "raw": data}
    except Exception:
        return {"id": reference, "status": "ERROR", "redirect_url": None}


def parse_provider_webhook(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Attempt to parse an external provider webhook payload into a standard dict with id and status.

    Tolerant to different provider payload shapes.
    """
    pay_id = payload.get("Id") or payload.get("id") or payload.get("paymentId")
    status = None
    for k in ("Status", "status", "PaymentStatus"):
        if k in payload:
            status = payload.get(k)
            break
    metadata = payload.get("Metadata") or payload.get("metadata") or {}
    reference = metadata.get("reference") if isinstance(metadata, dict) else None
    return {"id": pay_id, "status": status, "reference": reference, "raw": payload}
