from __future__ import annotations

import ssl
import urllib.request

import certifi


def trusted_https_context() -> ssl.SSLContext:
    """Return a certificate-validating TLS context backed by the bundled CA store."""
    context = ssl.create_default_context(cafile=certifi.where())
    context.check_hostname = True
    context.verify_mode = ssl.CERT_REQUIRED
    return context


def trusted_urlopen(request: urllib.request.Request, *, timeout: int | float):
    return urllib.request.urlopen(
        request,
        timeout=timeout,
        context=trusted_https_context(),
    )
