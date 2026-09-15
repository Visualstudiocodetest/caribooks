from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from jwt.exceptions import InvalidTokenError

ALGORITHM = "HS256"


def create_access_token(payload: dict[str, Any], secret_key: str, expires_minutes: int) -> str:
    to_encode = payload.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str, secret_key: str) -> dict[str, Any]:
    # `algorithms` is pinned to the single algorithm we sign with: without it,
    # PyJWT would accept any algorithm named in the token header, which is the
    # classic JWT algorithm-confusion attack.
    try:
        return jwt.decode(token, secret_key, algorithms=[ALGORITHM])
    except InvalidTokenError as exc:
        raise ValueError("Invalid or expired token") from exc
