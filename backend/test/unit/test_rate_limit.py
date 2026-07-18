from __future__ import annotations

import pytest
from fastapi import HTTPException

from services.rate_limit import check_rate_limit, reset_rate_limit


def test_check_rate_limit_allows_up_to_the_limit():
    key = "test:allow"
    reset_rate_limit(key)
    for _ in range(5):
        check_rate_limit(key, max_attempts=5, window_seconds=60)


def test_check_rate_limit_blocks_beyond_the_limit():
    key = "test:block"
    reset_rate_limit(key)
    for _ in range(3):
        check_rate_limit(key, max_attempts=3, window_seconds=60)
    with pytest.raises(HTTPException) as exc_info:
        check_rate_limit(key, max_attempts=3, window_seconds=60)
    assert exc_info.value.status_code == 429


def test_reset_rate_limit_clears_the_counter():
    key = "test:reset"
    reset_rate_limit(key)
    for _ in range(3):
        check_rate_limit(key, max_attempts=3, window_seconds=60)
    reset_rate_limit(key)
    check_rate_limit(key, max_attempts=3, window_seconds=60)  # does not raise
