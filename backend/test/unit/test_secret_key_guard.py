from __future__ import annotations

import importlib
import sys

import pytest


def _reload_deps():
    sys.modules.pop("presentation.deps", None)
    return importlib.import_module("presentation.deps")


@pytest.fixture(autouse=True)
def _restore_deps_module():
    # Reloading presentation.deps replaces the cached sys.modules entry; other
    # modules (auth_router, user_router, ...) keep their own already-bound
    # SECRET_KEY/ENVIRONMENT names, so this only affects fresh imports. Still,
    # reload once more after each test so sys.modules reflects the real env.
    yield
    _reload_deps()


def test_placeholder_secret_key_raises_regardless_of_environment(monkeypatch):
    """The fix for the SECRET_KEY fallback bug: a known/placeholder value must
    be rejected unconditionally, not just when ENVIRONMENT == 'production'."""
    monkeypatch.setenv("SECRET_KEY", "dev-secret-key")
    monkeypatch.setenv("ENVIRONMENT", "development")
    with pytest.raises(RuntimeError):
        _reload_deps()


def test_missing_secret_key_generates_random_value(monkeypatch):
    monkeypatch.delenv("SECRET_KEY", raising=False)
    mod = _reload_deps()
    assert mod.SECRET_KEY
    assert mod.SECRET_KEY not in ("", "dev-secret-key", "changeme", "secret", "change-me")


def test_strong_secret_key_is_accepted(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "a-sufficiently-long-random-value-123456")
    mod = _reload_deps()
    assert mod.SECRET_KEY == "a-sufficiently-long-random-value-123456"
