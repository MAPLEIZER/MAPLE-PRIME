from __future__ import annotations

import json
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import AppOwnershipLink, AppStoreObservation
from app.db.relationship_repository import EntityRelationshipRepository
from app.schemas.relationships import RelationshipEvidenceInput, RelationshipInput


def _utc_aware(value: datetime) -> datetime:
    # SQLite does not retain timezone metadata even for DateTime(timezone=True).
    # All KDR persisted timestamps are UTC, so re-attach UTC on read rather than
    # allowing a timezone-naive value into the evidence schema.
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def sync_app_ownership_relationships(session: Session, *, app_id: str | None = None) -> int:
    repo = EntityRelationshipRepository(session)
    statement = select(AppOwnershipLink).order_by(AppOwnershipLink.created_at)
    if app_id:
        statement = statement.where(AppOwnershipLink.app_id == app_id)
    edges = 0
    for link in session.scalars(statement):
        observation = session.scalar(
            select(AppStoreObservation)
            .where(AppStoreObservation.app_id == link.app_id)
            .order_by(AppStoreObservation.observed_at.desc(), AppStoreObservation.id.desc())
            .limit(1)
        )
        observed_at = _utc_aware(observation.observed_at if observation else link.created_at)
        relation = repo.record(
            RelationshipInput(
                subject_type="marketplace_app",
                subject_id=link.app_id,
                relationship_type="operated_by",
                object_type="institution",
                object_id=link.institution_id,
                confidence=link.confidence,
                observed_at=observed_at,
            )
        )
        edges += 1
        if link.review_state in {"confirmed", "rejected"} and relation.review_state == "candidate":
            repo.review(
                relation.id,
                decision=link.review_state,
                reviewer=link.reviewed_by or "legacy_review",
            )
        for signal in json.loads(link.signals_json):
            repo.add_evidence(
                relation.id,
                RelationshipEvidenceInput(
                    source_type="app_registry_match_signal",
                    source_url=observation.source_url if observation else None,
                    observed_at=observed_at,
                    evidence_strength=(
                        "strong"
                        if signal in {"cbk_published_email_exact", "website_domain_exact"}
                        else "moderate"
                    ),
                    evidence_text=signal,
                    structured_claim={
                        "signal": signal,
                        "legacy_app_ownership_link_id": link.id,
                    },
                ),
            )
    return edges
