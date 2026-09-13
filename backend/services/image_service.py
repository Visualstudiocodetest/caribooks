import hashlib
import ipaddress
import os
import socket
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin, urlparse, urlunparse

import httpx

# Only ever save formats a browser will render as an image, never execute as a
# document. SVG is deliberately excluded: it can embed <script>, which -- served
# back from our own /static origin -- would be a stored XSS, not just an SSRF risk.
_ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "webp", "avif", "bmp"}

# Anchored the same way main.py anchors its `/static` mount (relative to this
# file's own location, not the process's current working directory) -- so
# images always land inside the directory that's actually served, regardless
# of which directory the app was launched from.
_DEFAULT_SAVE_DIR = str(Path(__file__).resolve().parent.parent / "static" / "images" / "books")


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


def _resolve_pinned_ip(hostname: str) -> str:
    """Resolve `hostname` and return a single validated public IP to connect to.

    Callers must connect to *this exact IP* (not re-resolve the hostname) --
    otherwise there's a TOCTOU window (DNS rebinding): this check could pass
    against a public IP with a low TTL, and the real connection moments later
    could resolve the same attacker-controlled hostname to 127.0.0.1 or a
    cloud metadata address, defeating the allowlist entirely.
    """
    if not hostname:
        raise ValueError("Invalid URL")
    try:
        infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror as e:
        raise ValueError("Could not resolve host") from e
    ips = {info[4][0] for info in infos}
    if not ips or not all(_is_public_ip(ip) for ip in ips):
        raise ValueError("URL host is not allowed")
    # Prefer IPv4 for a simpler literal in the pinned URL; any validated
    # address works equally well since all of them were just checked.
    return next((ip for ip in ips if ":" not in ip), next(iter(ips)))


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


def _pin(url: str) -> tuple[str, dict, dict]:
    """Resolve `url`'s host to a validated public IP and return the connection
    target for httpx: (pinned_url, headers, extensions). See _resolve_pinned_ip
    for why the hostname must never be re-resolved once validated."""
    if not url or not url.lower().startswith(('http://', 'https://')):
        raise ValueError('Invalid URL')
    parsed = urlparse(url)
    hostname = parsed.hostname
    pinned_ip = _resolve_pinned_ip(hostname or '')
    ip_literal = f"[{pinned_ip}]" if ':' in pinned_ip else pinned_ip
    port_part = f":{parsed.port}" if parsed.port else ""
    pinned_url = urlunparse(parsed._replace(netloc=f"{ip_literal}{port_part}"))
    headers = {"Host": hostname} if hostname else {}
    extensions = {"sni_hostname": hostname} if hostname else {}
    return pinned_url, headers, extensions


def download_image(
    url: str,
    save_dir: str = _DEFAULT_SAVE_DIR,
    max_bytes: int = 5 * 1024 * 1024,
    max_redirects: int = 3,
) -> str:
    """
    Download an image from `url`, save it under `save_dir` (raw bytes) and return the relative path
    (eg. '/static/images/books/<hash>.jpg'). Raises Exception on failure.

    Redirects are followed manually (never httpx's own follow_redirects) up to
    `max_redirects` hops, re-validating and re-pinning the SSRF check on every
    hop -- blocking redirects outright would break real-world sources like
    OpenLibrary, whose cover URLs always 302 to an archive.org host; blindly
    following them with follow_redirects=True would let a first hop to an
    allowed public host redirect straight into 127.0.0.1/metadata addresses.
    """
    if not url or not url.lower().startswith(('http://', 'https://')):
        raise ValueError('Invalid URL')

    _ensure_dir(save_dir)
    # Filename is keyed on the originally-requested URL, not wherever
    # redirects end up, so repeated calls for the same source cache to the
    # same file even if the redirect target changes over time.
    h = hashlib.sha256(url.encode('utf-8')).hexdigest()

    current_url = url
    with httpx.Client(timeout=10.0, follow_redirects=False) as client:
        for _ in range(max_redirects + 1):
            pinned_url, headers, extensions = _pin(current_url)
            with client.stream('GET', pinned_url, timeout=10.0, headers=headers, extensions=extensions) as resp:
                if resp.status_code in (301, 302, 303, 307, 308):
                    location = resp.headers.get('location')
                    if not location:
                        raise ValueError('Redirect with no Location header')
                    current_url = urljoin(current_url, location)
                    continue
                resp.raise_for_status()
                content_type = resp.headers.get('content-type', '')
                ext = _ext_from_content_type(content_type)

                # fallback to extension from URL
                if not ext:
                    path_part = current_url.split('?')[0]
                    maybe = os.path.splitext(path_part)[1].lstrip('.').lower()
                    ext = maybe or 'jpg'

                if ext not in _ALLOWED_EXTENSIONS:
                    raise ValueError(f"Unsupported image type: {ext}")

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

    raise ValueError('Too many redirects')
