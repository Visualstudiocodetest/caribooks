"""Minimal in-memory rate limiter for auth endpoints.

Hand-rolled rather than pulling in a third-party rate-limiting library (KISS —
the app runs as a small number of Uvicorn workers on a single VM, so a
per-process fixed-window counter is sufficient; no Redis/shared state needed).
"""

from __future__ import annotations

import time
from collections import defaultdict

from fastapi import HTTPException, status

_attempts: dict[str, list[float]] = defaultdict(list)


def check_rate_limit(key: str, max_attempts: int, window_seconds: int) -> None:
    """Raise HTTP 429 if `key` has hit `max_attempts` within `window_seconds`."""
    now = time.monotonic()
    window_start = now - window_seconds
    recent = [t for t in _attempts[key] if t > window_start]
    if len(recent) >= max_attempts:
        _attempts[key] = recent
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many attempts. Please try again later.",
        )
    recent.append(now)
    _attempts[key] = recent


def reset_rate_limit(key: str) -> None:
    _attempts.pop(key, None)
