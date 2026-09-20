from __future__ import annotations

import re

from infrastructure import crud_user

# bcrypt hash shape: $2b$<cost>$<22-char-salt><31-char-hash>, all base64-alphabet.
_BCRYPT_RE = re.compile(r"^\$2b\$(\d{2})\$[A-Za-z0-9./]{53}$")


def test_hashing_the_same_password_twice_yields_different_hashes():
    """Proves the salt is per-call, not a fixed/reused value: two accounts
    sharing a password must not end up with the same stored hash."""
    h1 = crud_user.get_password_hash("correct horse battery staple")
    h2 = crud_user.get_password_hash("correct horse battery staple")
    assert h1 != h2
    assert crud_user.verify_password("correct horse battery staple", h1)
    assert crud_user.verify_password("correct horse battery staple", h2)


def test_hash_embeds_bcrypt_cost_factor_12():
    """The salt lives inside the bcrypt hash string itself (no separate salt
    column) -- this also pins the configured cost factor at 12."""
    h = crud_user.get_password_hash("some-password")
    m = _BCRYPT_RE.match(h)
    assert m is not None, f"unexpected hash format: {h!r}"
    assert int(m.group(1)) == 12


def test_verify_rejects_wrong_password():
    h = crud_user.get_password_hash("right-password")
    assert crud_user.verify_password("right-password", h)
    assert not crud_user.verify_password("wrong-password", h)


def test_verify_rejects_malformed_stored_hash_instead_of_raising():
    assert crud_user.verify_password("anything", "not-a-real-hash") is False
