from __future__ import annotations

import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.local_actions import require_relationship_action, require_relationship_review_action
from app.db.models import AppOwnershipLink, AppStoreObservation
from app.db.relationship_repository import EntityRelationshipRepository
from app.db.session import get_session
from app.schemas.relationships import (
    RelationshipEvidenceInput,
    RelationshipInput,
    RelationshipReviewInput,
)

router = APIRouter(prefix="/api/v1/relationships", tags=["entity relationships"])
DbSession = Annotated[Session, Depends(get_session)]


def _serialize(repo: EntityRelationshipRepository, item) -> dict[str, object]:
    return {
        "id": item.id,
        "subject_type": item.subject_type,
        "subject_id": item.subject_id,
        "relationship_type": item.relationship_type,
        "object_type": item.object_type,
        "object_id": item.object_id,
        "confidence": item.confidence,
        "review_state": item.review_state,
        "methodology_version": item.methodology_version,
        "reviewed_by": item.reviewed_by,
        "reviewed_at": item.reviewed_at.isoformat() if item.reviewed_at else None,
        "first_seen_at": item.first_seen_at.isoformat(),
        "last_seen_at": item.last_seen_at.isoformat(),
        "evidence": [
            {
                "id": evidence.id,
                "source_type": evidence.source_type,
                "source_url": evidence.source_url,
                "source_snapshot_id": evidence.source_snapshot_id,
                "source_observation_id": evidence.source_observation_id,
                "observed_at": evidence.observed_at.isoformat(),
                "evidence_strength": evidence.evidence_strength,
                "evidence_text": evidence.evidence_text,
                "structured_claim": json.loads(evidence.structured_claim_json),
                "evidence_fingerprint": evidence.evidence_fingerprint,
            }
            for evidence in repo.evidence_for(item.id)
        ],
    }


@router.get("")
def list_relationships(
    session: DbSession,
    subject_id: str | None = Query(default=None, max_length=160),
    object_id: str | None = Query(default=None, max_length=160),
    relationship_type: str | None = Query(default=None, max_length=60),
    limit: int = Query(default=500, ge=1, le=1000),
) -> list[dict[str, object]]:
    repo = EntityRelationshipRepository(session)
    return [
        _serialize(repo, item)
        for item in repo.list(
            subject_id=subject_id,
            object_id=object_id,
            relationship_type=relationship_type,
            limit=limit,
        )
    ]


@router.post("", dependencies=[Depends(require_relationship_action)])
def record_relationship(payload: RelationshipInput, session: DbSession) -> dict[str, object]:
    repo = EntityRelationshipRepository(session)
    item = repo.record(payload)
    session.commit()
    return _serialize(repo, item)


@router.post("/{relationship_id}/evidence", dependencies=[Depends(require_relationship_action)])
def add_relationship_evidence(
    relationship_id: str,
    payload: RelationshipEvidenceInput,
    session: DbSession,
) -> dict[str, object]:
    repo = EntityRelationshipRepository(session)
    try:
        repo.add_evidence(relationship_id, payload)
        session.commit()
        item = repo.get(relationship_id)
        assert item is not None
        return _serialize(repo, item)
    except KeyError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="relationship not found") from exc


@router.post("/{relationship_id}/review", dependencies=[Depends(require_relationship_review_action)])
def review_relationship(
    relationship_id: str,
    payload: RelationshipReviewInput,
    session: DbSession,
) -> dict[str, object]:
    repo = EntityRelationshipRepository(session)
    try:
        item = repo.review(relationship_id, decision=payload.decision, reviewer="local_user")
        session.commit()
        return _serialize(repo, item)
    except KeyError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="relationship not found") from exc


@router.post("/backfill/app-ownership", dependencies=[Depends(require_relationship_action)])
def backfill_app_ownership(session: DbSession) -> dict[str, int]:
    repo = EntityRelationshipRepository(session)
    created_or_seen = 0
    evidence_seen = 0
    for link in session.scalars(select(AppOwnershipLink).order_by(AppOwnershipLink.created_at)):
        observation = session.scalar(
            select(AppStoreObservation)
            .where(AppStoreObservation.app_id == link.app_id)
            .order_by(AppStoreObservation.observed_at.desc(), AppStoreObservation.id.desc())
            .limit(1)
        )
        relation = repo.record(
            RelationshipInput(
                subject_type="marketplace_app",
                subject_id=link.app_id,
                relationship_type="operated_by",
                object_type="institution",
                object_id=link.institution_id,
                confidence=link.confidence,
                observed_at=observation.observed_at if observation else link.created_at,
            )
        )
        created_or_seen += 1
        if link.review_state in {"confirmed", "rejected"} and relation.review_state == "candidate":
            repo.review(relation.id, decision=link.review_state, reviewer=link.reviewed_by or "legacy_review")
        for signal in json.loads(link.signals_json):
            repo.add_evidence(
                relation.id,
                RelationshipEvidenceInput(
                    source_type="app_registry_match_signal",
                    source_url=observation.source_url if observation else None,
                    observed_at=observation.observed_at if observation else link.created_at,
                    evidence_strength="strong" if signal in {"cbk_published_email_exact", "website_domain_exact"} else "moderate",
                    evidence_text=signal,
                    structured_claim={"signal": signal, "legacy_app_ownership_link_id": link.id},
                ),
            )
            evidence_seen += 1
    session.commit()
    return {"relationships_seen": created_or_seen, "evidence_seen": evidence_seen}
