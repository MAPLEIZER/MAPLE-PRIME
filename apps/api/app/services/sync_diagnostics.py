from __future__ import annotations

from app.services.fetcher import SourceFetchError

_SAFE_MESSAGES = {
    "source_access_restricted": "The official source refused automated access. Retry later or open the official source manually.",
    "source_redirect": "The official source redirected unexpectedly and requires source-manifest review.",
    "source_timeout": "The official source timed out before KDR could finish the sync.",
    "source_unavailable": "The official source is temporarily unavailable. Retry later.",
    "source_response_too_large": "The official source exceeded KDR's configured download safety limit.",
    "source_network_error": "KDR could not establish a trusted network connection to the official source.",
    "source_fetch_failed": "KDR could not download the official source.",
    "source_format_changed": "The downloaded official source did not match KDR's expected format and was not imported.",
    "unsupported_parser": "This source does not yet have an enabled importer.",
    "local_storage_error": "KDR could not safely persist the source snapshot locally.",
}


def public_sync_failure(source_id: str, exc: Exception) -> dict[str, str]:
    if isinstance(exc, SourceFetchError):
        code = exc.code
    elif isinstance(exc, OSError):
        code = "local_storage_error"
    else:
        code = "source_format_changed"
    return {
        "source_id": source_id,
        "code": code,
        "message": _SAFE_MESSAGES.get(code, _SAFE_MESSAGES["source_fetch_failed"]),
    }
