from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from jose import jwt


def create_access_token(payload: dict[str, Any], secret_key: str, expires_minutes: int) -> str:
    to_encode = payload.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, secret_key, algorithm="HS256")


def decode_access_token(token: str, secret_key: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, secret_key, algorithms=["HS256"])
    except Exception as exc:
        raise ValueError("Invalid or expired token") from exc

