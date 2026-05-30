from __future__ import annotations

import os
from typing import Optional, Dict, Any

import httpx

PAYREXX_API_KEY = os.getenv("PAYREXX_API_KEY")
PAYREXX_BASE = os.getenv("PAYREXX_BASE_URL", "https://api.payrexx.com/v1")


def create_payrexx_payment(amount_chf: float, reference: str, return_url: str, cancel_url: str, description: str) -> Dict[str, Any]:
    """Create a Payrexx payment and return provider response including a redirect URL.

    If PAYREXX_API_KEY is not configured, returns a local simulated URL for testing.
    """
    amount = int(round(amount_chf * 100))  # cents

    if not PAYREXX_API_KEY:
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

    headers = {"Authorization": f"Bearer {PAYREXX_API_KEY}", "Content-Type": "application/json"}
    url = PAYREXX_BASE.rstrip("/") + "/Payment"

    try:
        with httpx.Client(timeout=10.0) as client:
            r = client.post(url, json=payload, headers=headers)
            r.raise_for_status()
            data = r.json()
            # The exact structure depends on Payrexx API version; try to extract a checkout link
            redirect = None
            if isinstance(data, dict):
                # Common fields: data.get('Url') or nested Link
                redirect = data.get("Url") or data.get("url")
                if not redirect:
                    # try nested
                    for k in ("Payment", "payment", "data"):
                        sub = data.get(k)
                        if isinstance(sub, dict):
                            redirect = sub.get("Url") or sub.get("url") or redirect
            return {"id": data.get("Id") or data.get("id") or reference, "status": "CREATED", "redirect_url": redirect, "raw": data}
    except Exception:
        return {"id": reference, "status": "ERROR", "redirect_url": None}


def parse_webhook(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Attempt to parse a Payrexx webhook payload into a standard dict with id and status.

    This is tolerant to different payload shapes used by Payrexx versions.
    """
    # Try common fields
    pay_id = payload.get("Id") or payload.get("id") or payload.get("paymentId")
    status = None
    # common status fields
    for k in ("Status", "status", "PaymentStatus"):
        if k in payload:
            status = payload.get(k)
            break
    # metadata reference
    metadata = payload.get("Metadata") or payload.get("metadata") or {}
    reference = metadata.get("reference") if isinstance(metadata, dict) else None
    return {"id": pay_id, "status": status, "reference": reference, "raw": payload}
