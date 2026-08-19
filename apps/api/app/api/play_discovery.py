from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.local_actions import require_play_discovery_action
from app.db.session import get_session
from app.services.play_store_discovery import run_cbk_play_discovery

router = APIRouter(prefix="/api/v1/apps/discovery", tags=["app discovery"])
DbSession = Annotated[Session, Depends(get_session)]


@router.post("/run", dependencies=[Depends(require_play_discovery_action)])
def run_play_discovery(
    session: DbSession,
    max_providers: int = Query(default=25, ge=1, le=50),
    max_apps: int = Query(default=100, ge=1, le=200),
) -> dict[str, object]:
    result = run_cbk_play_discovery(
        session,
        max_providers=max_providers,
        max_apps=max_apps,
    )
    session.commit()
    return {
        "providers_considered": result.providers_considered,
        "search_requests": result.search_requests,
        "detail_requests": result.detail_requests,
        "apps_ingested": result.apps_ingested,
        "ownership_candidates": result.ownership_candidates,
        "relationship_edges": result.relationship_edges,
        "failures": list(result.failures),
    }
