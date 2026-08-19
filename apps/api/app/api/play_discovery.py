import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.local_actions import require_play_discovery_action
from app.core.config import get_settings
from app.db.session import get_session
from app.services.play_discovery_provider import (
    resolve_settings_provider,
    run_configured_play_discovery,
)
from app.services.play_store_discovery import PlayDiscoveryUnavailable
from app.services.serpapi_account import check_serpapi_account

router = APIRouter(prefix="/api/v1/apps/discovery", tags=["app discovery"])
DbSession = Annotated[Session, Depends(get_session)]
logger = logging.getLogger(__name__)


def _serpapi_preflight() -> dict[str, object] | None:
    settings = get_settings()
    resolved = resolve_settings_provider(settings)
    if resolved.provider != "serpapi":
        return None

    health = check_serpapi_account(resolved.serpapi_api_key)
    if not health.get("checked") or health.get("key_valid") is None:
        return health
    if health.get("key_valid") is False:
        raise PlayDiscoveryUnavailable(
            str(health.get("error") or "SerpApi reports that the configured API key is invalid")
        )

    account_status = str(health.get("account_status") or "").strip()
    if account_status and account_status.casefold() != "active":
        raise PlayDiscoveryUnavailable(
            str(
                health.get("error")
                or f"SerpApi account is {account_status}; the key is recognized but search permission is unavailable"
            )
        )
    if health.get("searches_left") == 0:
        raise PlayDiscoveryUnavailable(
            str(health.get("error") or "SerpApi account has no searches remaining")
        )
    return health


def _diagnostic_failures(
    failures: tuple[str, ...],
    account_health: dict[str, object] | None,
) -> list[str]:
    result: list[str] = []
    key_recognized = bool(account_health and account_health.get("key_valid") is True)
    account_status = str(account_health.get("account_status") or "") if account_health else ""
    for failure in failures:
        if key_recognized and "rejected the configured api key" in failure.casefold():
            suffix = f" Account API status: {account_status}." if account_status else ""
            result.append(
                "SerpApi Account API recognizes this key, but the Google Play Search API rejected the request. "
                f"This indicates a search permission/account restriction rather than a missing local key.{suffix}"
            )
        else:
            result.append(failure)
    return list(dict.fromkeys(result))


@router.get("/status")
def play_discovery_status() -> dict[str, object]:
    settings = get_settings()
    requested = settings.play_discovery_provider.strip().lower() or "auto"
    try:
        resolved = resolve_settings_provider(settings)
        configured = True
        configuration_error = None
    except PlayDiscoveryUnavailable as exc:
        resolved = None
        configured = False
        configuration_error = str(exc)
    return {
        "requested_provider": requested,
        "active_provider": resolved.provider if resolved else requested,
        "configured": configured,
        "serpapi_key_configured": bool(settings.serpapi_api_key),
        "talordata_key_configured": bool(settings.talordata_api_key),
        "public_html_fallback_available": True,
        "manual_batch": {"max_providers": 5, "max_apps": 15},
        "configuration_error": configuration_error,
        "configuration_note": resolved.configuration_note if resolved else None,
        "available_providers": ["talordata", "serpapi", "public_html"],
    }


@router.get("/account")
def play_discovery_account() -> dict[str, object]:
    """Return redacted SerpApi.com account/usage health when that provider is active."""

    settings = get_settings()
    resolved = resolve_settings_provider(settings)
    if resolved.provider != "serpapi":
        return {
            "checked": False,
            "key_valid": None,
            "account_status": None,
            "plan_name": None,
            "searches_left": None,
            "this_month_usage": None,
            "this_hour_searches": None,
            "hourly_limit": None,
            "plan_renewal_date": None,
            "error": f"SerpApi.com account health is not applicable while {resolved.provider} is active.",
        }
    return check_serpapi_account(resolved.serpapi_api_key)


@router.post("/run", dependencies=[Depends(require_play_discovery_action)])
def run_play_discovery(
    session: DbSession,
    max_providers: int = Query(default=5, ge=1, le=50),
    max_apps: int = Query(default=15, ge=1, le=200),
) -> dict[str, object]:
    try:
        account_health = _serpapi_preflight()
        result = run_configured_play_discovery(
            session,
            max_providers=max_providers,
            max_apps=max_apps,
        )
        session.commit()
    except PlayDiscoveryUnavailable as exc:
        session.rollback()
        logger.warning("Play discovery provider unavailable: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "play_discovery_provider_unavailable",
                "message": str(exc),
            },
        ) from exc
    except Exception:
        session.rollback()
        logger.exception("Play discovery failed unexpectedly")
        raise

    warnings = _diagnostic_failures(result.failures, account_health)
    logger.info(
        "Play discovery completed provider=%s searches=%d details=%d apps=%d candidates=%d relationships=%d warnings=%s account=%s",
        result.provider,
        result.search_requests,
        result.detail_requests,
        result.apps_ingested,
        result.ownership_candidates,
        result.relationship_edges,
        warnings,
        {
            "status": account_health.get("account_status") if account_health else None,
            "searches_left": account_health.get("searches_left") if account_health else None,
        },
    )
    return {
        "provider": result.provider,
        "providers_considered": result.providers_considered,
        "search_requests": result.search_requests,
        "detail_requests": result.detail_requests,
        "apps_ingested": result.apps_ingested,
        "ownership_candidates": result.ownership_candidates,
        "relationship_edges": result.relationship_edges,
        "failures": warnings,
    }
