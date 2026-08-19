from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.local_actions import (
    require_app_import_action,
    require_app_reconcile_action,
    require_app_review_action,
)
from app.db.repositories import AppRegistryRepository, InstitutionRepository
from app.db.session import get_session
from app.schemas.apps import AppOwnershipReviewInput, PlayAppImportBatch

router = APIRouter(prefix="/api/v1/apps", tags=["app identity registry"])
DbSession = Annotated[Session, Depends(get_session)]


def _serialize_app(
    repository: AppRegistryRepository,
    institutions: InstitutionRepository,
    app,
    *,
    public_export: bool = False,
) -> dict[str, object]:
    observation = repository.latest_observation(app.id)
    links = []
    for link in repository.links_for_app(app.id):
        if public_export and link.review_state == "rejected":
            continue
        institution = institutions.get(link.institution_id)
        links.append(
            {
                "id": link.id,
                "institution_id": link.institution_id,
                "institution_name": institution.legal_name if institution else None,
                "confidence": link.confidence,
                "signals": json.loads(link.signals_json),
                "review_state": link.review_state,
                "reviewed_by": link.reviewed_by,
                "reviewed_at": link.reviewed_at.isoformat() if link.reviewed_at else None,
            }
        )
    return {
        "id": app.id,
        "store": app.store,
        "package_name": app.package_name,
        "loan_relevance": app.loan_relevance,
        "first_seen_at": app.first_seen_at.isoformat(),
        "last_seen_at": app.last_seen_at.isoformat(),
        "app_name": observation.app_name if observation else None,
        "developer_name": observation.developer_name if observation else None,
        "developer_id": observation.developer_id if observation else None,
        "support_email": observation.support_email if observation else None,
        "email_domain": observation.email_domain if observation else None,
        "developer_website": observation.developer_website if observation else None,
        "developer_domain": observation.developer_domain if observation else None,
        "privacy_policy_url": observation.privacy_policy_url if observation else None,
        "store_url": observation.store_url if observation else None,
        "category": observation.category if observation else None,
        "installs": observation.installs if observation else None,
        "source_provider": observation.source_provider if observation else None,
        "source_url": observation.source_url if observation else None,
        "observed_at": observation.observed_at.isoformat() if observation else None,
        "ownership_links": links,
    }


@router.get("")
def list_apps(
    session: DbSession,
    email: str | None = Query(default=None, max_length=320),
    domain: str | None = Query(default=None, max_length=255),
    q: str | None = Query(default=None, max_length=200),
    limit: int = Query(default=500, ge=1, le=1000),
) -> list[dict[str, object]]:
    repository = AppRegistryRepository(session)
    if email:
        apps = repository.find_by_email(email)
    elif domain:
        apps = repository.find_by_domain(domain)
    else:
        apps = repository.list_apps(limit=limit)
    if q:
        needle = q.casefold().strip()
        filtered = []
        for app in apps:
            observation = repository.latest_observation(app.id)
            haystack = " ".join(
                value
                for value in (
                    app.package_name,
                    observation.app_name if observation else None,
                    observation.developer_name if observation else None,
                    observation.support_email if observation else None,
                    observation.developer_domain if observation else None,
                )
                if value
            ).casefold()
            if needle in haystack:
                filtered.append(app)
        apps = filtered
    institutions = InstitutionRepository(session)
    return [_serialize_app(repository, institutions, app) for app in apps[:limit]]


@router.get("/summary")
def app_registry_summary(session: DbSession) -> dict[str, int]:
    repository = AppRegistryRepository(session)
    apps = repository.list_apps(limit=1000)
    confirmed = 0
    candidates = 0
    for app in apps:
        for link in repository.links_for_app(app.id):
            if link.review_state == "confirmed":
                confirmed += 1
            elif link.review_state == "candidate":
                candidates += 1
    return {
        "apps": len(apps),
        "confirmed_ownership_links": confirmed,
        "candidate_ownership_links": candidates,
    }


@router.get("/export")
def export_app_registry(session: DbSession) -> dict[str, object]:
    repository = AppRegistryRepository(session)
    institutions = InstitutionRepository(session)
    apps = repository.list_apps(limit=1000)
    return {
        "schema_version": "kdr-app-registry-v1",
        "generated_at": datetime.now(UTC).isoformat(),
        "disclaimer": (
            "Public marketplace observations and evidence links. Candidate ownership links "
            "require review and are not legal findings or regulator determinations."
        ),
        "records": [
            _serialize_app(repository, institutions, app, public_export=True)
            for app in apps
        ],
    }


@router.post("/import/play", dependencies=[Depends(require_app_import_action)])
def import_play_apps(payload: PlayAppImportBatch, session: DbSession) -> dict[str, int]:
    repository = AppRegistryRepository(session)
    app_ids: set[str] = set()
    observations_before = 0
    candidates = 0
    try:
        for item in payload.records:
            app = repository.ingest_play(item)
            app_ids.add(app.id)
        for app_id in app_ids:
            observations_before += len(repository.observations(app_id))
            candidates += len(repository.generate_candidates(app_id))
        session.commit()
    except Exception:
        session.rollback()
        raise
    return {
        "apps_touched": len(app_ids),
        "observations_available": observations_before,
        "ownership_candidates": candidates,
    }


@router.post("/{app_id}/ownership/reconcile", dependencies=[Depends(require_app_reconcile_action)])
def reconcile_app_ownership(app_id: str, session: DbSession) -> dict[str, int]:
    repository = AppRegistryRepository(session)
    try:
        links = repository.generate_candidates(app_id)
        session.commit()
    except KeyError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="app not found") from exc
    except Exception:
        session.rollback()
        raise
    return {"candidate_count": len(links)}


@router.post("/ownership/{link_id}/review", dependencies=[Depends(require_app_review_action)])
def review_app_ownership(
    link_id: str,
    payload: AppOwnershipReviewInput,
    session: DbSession,
) -> dict[str, object]:
    repository = AppRegistryRepository(session)
    try:
        link = repository.review_link(link_id, decision=payload.decision, reviewer="local_user")
        session.commit()
    except KeyError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ownership link not found") from exc
    except Exception:
        session.rollback()
        raise
    return {
        "id": link.id,
        "review_state": link.review_state,
        "reviewed_by": link.reviewed_by,
        "reviewed_at": link.reviewed_at.isoformat() if link.reviewed_at else None,
    }


@router.get("/{app_id}/history")
def app_history(app_id: str, session: DbSession) -> list[dict[str, object]]:
    repository = AppRegistryRepository(session)
    if repository.get(app_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="app not found")
    return [
        {
            "id": item.id,
            "observed_at": item.observed_at.isoformat(),
            "app_name": item.app_name,
            "developer_name": item.developer_name,
            "developer_id": item.developer_id,
            "support_email": item.support_email,
            "developer_website": item.developer_website,
            "privacy_policy_url": item.privacy_policy_url,
            "store_url": item.store_url,
            "source_provider": item.source_provider,
            "source_url": item.source_url,
        }
        for item in repository.observations(app_id, limit=500)
    ]
