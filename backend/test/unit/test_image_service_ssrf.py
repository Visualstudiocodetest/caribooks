from __future__ import annotations

import pytest

from services.image_service import _assert_safe_url, _is_public_ip, download_image


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


def test_assert_safe_url_rejects_loopback_and_metadata_hosts():
    with pytest.raises(ValueError):
        _assert_safe_url("http://127.0.0.1/secret")
    with pytest.raises(ValueError):
        _assert_safe_url("http://169.254.169.254/latest/meta-data/")
    with pytest.raises(ValueError):
        _assert_safe_url("http://localhost/x")


def test_download_image_rejects_ssrf_targets_without_making_a_request():
    for url in (
        "http://127.0.0.1:8000/admin",
        "http://169.254.169.254/latest/meta-data/iam/security-credentials/",
        "http://10.0.0.5/internal",
        "ftp://example.com/x",
    ):
        with pytest.raises(Exception):
            download_image(url)
