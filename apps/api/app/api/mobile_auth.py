from __future__ import annotations

import secrets
from typing import Annotated

from fastapi import Header, HTTPException, status

from app.core.config import get_settings


def validate_mobile_bearer(
    authorization: str | None,
    *,
    enabled: bool,
    configured_token: str | None,
) -> str:
    if not enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="mobile telemetry is disabled",
        )
    if not configured_token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="mobile telemetry is not paired",
        )
    prefix = "Bearer "
    if not authorization or not authorization.startswith(prefix):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="invalid mobile credential")
    supplied = authorization[len(prefix) :]
    if not secrets.compare_digest(supplied, configured_token):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="invalid mobile credential")
    return supplied


def require_mobile_bearer(
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
) -> str:
    settings = get_settings()
    return validate_mobile_bearer(
        authorization,
        enabled=settings.mobile_telemetry_enabled,
        configured_token=settings.mobile_api_token,
    )
