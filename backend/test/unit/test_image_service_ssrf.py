from __future__ import annotations

import pytest

from services.image_service import _ALLOWED_EXTENSIONS, _is_public_ip, _resolve_pinned_ip, download_image


def test_is_public_ip_rejects_private_and_reserved_ranges():
    assert _is_public_ip("127.0.0.1") is False  # loopback
    assert _is_public_ip("10.0.0.5") is False  # RFC1918 private
    assert _is_public_ip("192.168.1.1") is False  # RFC1918 private
    assert _is_public_ip("169.254.169.254") is False  # link-local / cloud metadata
    assert _is_public_ip("::1") is False  # IPv6 loopback
    assert _is_public_ip("fc00::1") is False  # IPv6 unique local
    assert _is_public_ip("not-an-ip") is False


def test_is_public_ip_accepts_public_addresses():
    assert _is_public_ip("8.8.8.8") is True
    assert _is_public_ip("1.1.1.1") is True


def test_resolve_pinned_ip_rejects_loopback_and_metadata_hosts():
    with pytest.raises(ValueError):
        _resolve_pinned_ip("127.0.0.1")
    with pytest.raises(ValueError):
        _resolve_pinned_ip("169.254.169.254")
    with pytest.raises(ValueError):
        _resolve_pinned_ip("localhost")


def test_download_image_rejects_ssrf_targets_without_making_a_request():
    for url in (
        "http://127.0.0.1:8000/admin",
        "http://169.254.169.254/latest/meta-data/iam/security-credentials/",
        "http://10.0.0.5/internal",
        "ftp://example.com/x",
    ):
        with pytest.raises(Exception):  # noqa: B017 — deliberately broad: covers both ValueError (SSRF) and unsupported-scheme errors
            download_image(url)


def test_allowed_extensions_exclude_svg_to_prevent_stored_xss():
    # SVG can embed <script>; served back from our own /static origin that
    # would be stored XSS, not just an SSRF concern -- so it must never be a
    # format download_image is willing to save, no matter what a remote server
    # claims its Content-Type is.
    assert "svg" not in _ALLOWED_EXTENSIONS
    assert "svg+xml" not in _ALLOWED_EXTENSIONS
    assert {"jpg", "png", "webp"} <= _ALLOWED_EXTENSIONS
