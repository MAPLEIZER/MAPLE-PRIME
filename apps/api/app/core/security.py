from __future__ import annotations

import ipaddress
from urllib.parse import urlsplit


class UnsafeOutboundURL(ValueError):
    pass


def validate_outbound_url(value: str) -> str:
    parsed = urlsplit(value)
    if parsed.scheme != "https":
        raise UnsafeOutboundURL("only HTTPS outbound URLs are allowed")
    if not parsed.hostname or parsed.username or parsed.password:
        raise UnsafeOutboundURL("invalid outbound URL")
    hostname = parsed.hostname.rstrip(".").lower()
    if hostname == "localhost" or hostname.endswith(".localhost"):
        raise UnsafeOutboundURL("local hosts are blocked")
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        return value
    if any(
        (
            address.is_private,
            address.is_loopback,
            address.is_link_local,
            address.is_multicast,
            address.is_reserved,
            address.is_unspecified,
        )
    ):
        raise UnsafeOutboundURL("non-public IP targets are blocked")
    return value
