import ipaddress
import os
import hashlib
import socket
from typing import Optional
from urllib.parse import urlparse

import httpx


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def _is_public_ip(ip_str: str) -> bool:
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return False
    return not (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def _assert_safe_url(url: str) -> None:
    """Block SSRF: reject any URL whose host resolves to a private/loopback/
    link-local/reserved address (this includes cloud metadata endpoints like
    169.254.169.254 and internal services on the VM's own network)."""
    hostname = urlparse(url).hostname
    if not hostname:
        raise ValueError("Invalid URL")
    try:
        infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        raise ValueError("Could not resolve host")
    if not infos or not all(_is_public_ip(info[4][0]) for info in infos):
        raise ValueError("URL host is not allowed")


def _ext_from_content_type(ct: str) -> Optional[str]:
    if not ct:
        return None
    ct = ct.lower()
    if ct.startswith('image/'):
        ext = ct.split('image/')[-1].split(';')[0].strip()
        if ext == 'jpeg':
            return 'jpg'
        # guard simple cases
        if '/' in ext or ext == '':
            return None
        return ext
    return None


def download_image(url: str, save_dir: str = 'static/images/books', max_bytes: int = 5 * 1024 * 1024) -> str:
    """
    Download an image from `url`, save it under `save_dir` (raw bytes) and return the relative path
    (eg. '/static/images/books/<hash>.jpg'). Raises Exception on failure.
    """
    if not url or not url.lower().startswith(('http://', 'https://')):
        raise ValueError('Invalid URL')
    _assert_safe_url(url)

    _ensure_dir(save_dir)

    # Use a stable filename based on the URL
    h = hashlib.sha256(url.encode('utf-8')).hexdigest()

    # Redirects are not followed: a redirect to an internal/private address
    # would otherwise bypass the _assert_safe_url check above.
    with httpx.Client(timeout=10.0, follow_redirects=False) as client:
        with client.stream('GET', url, timeout=10.0) as resp:
            if resp.status_code in (301, 302, 303, 307, 308):
                raise ValueError('Redirects are not allowed')
            resp.raise_for_status()
            content_type = resp.headers.get('content-type', '')
            ext = _ext_from_content_type(content_type)

            # fallback to extension from URL
            if not ext:
                path_part = url.split('?')[0]
                maybe = os.path.splitext(path_part)[1].lstrip('.')
                ext = maybe or 'jpg'

            filename = f"{h}.{ext}"
            tmp_path = os.path.join(save_dir, f"{h}.tmp")
            final_path = os.path.join(save_dir, filename)

            # If already exists, return quickly
            if os.path.exists(final_path):
                return f"/static/images/books/{filename}"

            bytes_written = 0
            with open(tmp_path, 'wb') as f:
                for chunk in resp.iter_bytes():
                    if not chunk:
                        continue
                    bytes_written += len(chunk)
                    if bytes_written > max_bytes:
                        # cleanup
                        try:
                            f.close()
                        except Exception:
                            pass
                        try:
                            os.remove(tmp_path)
                        except Exception:
                            pass
                        raise Exception('Image too large')
                    f.write(chunk)

            os.replace(tmp_path, final_path)

    return f"/static/images/books/{filename}"
