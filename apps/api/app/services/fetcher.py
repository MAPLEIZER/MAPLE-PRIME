from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlsplit

import httpx

from app.core.security import UnsafeOutboundURL, validate_outbound_url
from app.services.sources import SourceDefinition

APPROVED_SOURCE_HOSTS = frozenset(
    {
        "centralbank.go.ke",
        "www.centralbank.go.ke",
        "odpc.go.ke",
        "www.odpc.go.ke",
        "new.kenyalaw.org",
    }
)
DEFAULT_MAX_BYTES = 20 * 1024 * 1024


class SourceFetchError(RuntimeError):
    pass


@dataclass(frozen=True)
class FetchedSource:
    source_id: str
    url: str
    media_type: str
    body: bytes


def fetch_source(
    source: SourceDefinition,
    *,
    transport: httpx.BaseTransport | None = None,
    max_bytes: int = DEFAULT_MAX_BYTES,
) -> FetchedSource:
    try:
        validate_outbound_url(source.url)
    except UnsafeOutboundURL as exc:
        raise SourceFetchError(str(exc)) from exc

    hostname = (urlsplit(source.url).hostname or "").lower()
    if hostname not in APPROVED_SOURCE_HOSTS:
        raise SourceFetchError(f"source host is not in the approved allowlist: {hostname}")

    headers = {"User-Agent": "KenyaDataRights/0.1-alpha (+source-sync)"}
    try:
        with httpx.Client(
            transport=transport,
            follow_redirects=False,
            timeout=httpx.Timeout(30.0, connect=10.0),
            headers=headers,
        ) as client:
            with client.stream("GET", source.url) as response:
                if 300 <= response.status_code < 400:
                    raise SourceFetchError("source redirects are rejected and require manifest review")
                response.raise_for_status()
                declared = response.headers.get("content-length")
                if declared and int(declared) > max_bytes:
                    raise SourceFetchError("source response exceeds configured size limit")
                chunks: list[bytes] = []
                total = 0
                for chunk in response.iter_bytes():
                    total += len(chunk)
                    if total > max_bytes:
                        raise SourceFetchError("source response exceeds configured size limit")
                    chunks.append(chunk)
                media_type = response.headers.get("content-type", "application/octet-stream")
                media_type = media_type.split(";", 1)[0].strip().lower()
                return FetchedSource(
                    source_id=source.id,
                    url=source.url,
                    media_type=media_type,
                    body=b"".join(chunks),
                )
    except SourceFetchError:
        raise
    except (httpx.HTTPError, ValueError) as exc:
        raise SourceFetchError(f"source fetch failed: {exc}") from exc
