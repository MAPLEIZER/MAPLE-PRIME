import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.local_actions import require_play_discovery_action
from app.core.config import get_settings
from app.db.session import get_session
from app.services.play_store_discovery import (
    PlayDiscoveryUnavailable,
    run_cbk_play_discovery,
    selected_discovery_provider,
)
from app.services.serpapi_account import check_serpapi_account

router = APIRouter(prefix="/api/v1/apps/discovery", tags=["app discovery"])
DbSession = Annotated[Session, Depends(get_session)]
logger = logging.getLogger(__name__)


@router.get("/status")
def play_discovery_status() -> dict[str, object]:
    settings = get_settings()
    requested = settings.play_discovery_provider.strip().lower() or "auto"
    try:
        active = selected_discovery_provider(
            requested,
            serpapi_api_key=settings.serpapi_api_key,
        )
        configured = True
        configuration_error = None
    except PlayDiscoveryUnavailable as exc:
        active = requested
        configured = False
        configuration_error = str(exc)
    return {
        "requested_provider": requested,
        "active_provider": active,
        "configured": configured,
        "serpapi_key_configured": bool(settings.serpapi_api_key),
        "public_html_fallback_available": True,
        "manual_batch": {"max_providers": 5, "max_apps": 15},
        "configuration_error": configuration_error,
    }


@router.get("/account")
def play_discovery_account() -> dict[str, object]:
    """Return redacted SerpApi account/usage health without consuming a search."""

    settings = get_settings()
    return check_serpapi_account(settings.serpapi_api_key)


@router.post("/run", dependencies=[Depends(require_play_discovery_action)])
def run_play_discovery(
    session: DbSession,
    max_providers: int = Query(default=5, ge=1, le=50),
    max_apps: int = Query(default=15, ge=1, le=200),
) -> dict[str, object]:
    try:
        result = run_cbk_play_discovery(
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

    logger.info(
        "Play discovery completed provider=%s searches=%d details=%d apps=%d candidates=%d relationships=%d warnings=%s",
        result.provider,
        result.search_requests,
        result.detail_requests,
        result.apps_ingested,
        result.ownership_candidates,
        result.relationship_edges,
        list(result.failures),
    )
    return {
        "provider": result.provider,
        "providers_considered": result.providers_considered,
        "search_requests": result.search_requests,
        "detail_requests": result.detail_requests,
        "apps_ingested": result.apps_ingested,
        "ownership_candidates": result.ownership_candidates,
        "relationship_edges": result.relationship_edges,
        "failures": list(result.failures),
    }
