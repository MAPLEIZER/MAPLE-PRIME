from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.relationship_models import EntityRelationship, RelationshipEvidence
from app.schemas.relationships import RelationshipEvidenceInput, RelationshipInput


class EntityRelationshipRepository:
    VALID_DECISIONS = frozenset({"confirmed", "rejected"})

    def __init__(self, session: Session):
        self.session = session

    def get(self, relationship_id: str) -> EntityRelationship | None:
        return self.session.get(EntityRelationship, relationship_id)

    def find(
        self,
        *,
        subject_type: str,
        subject_id: str,
        relationship_type: str,
        object_type: str,
        object_id: str,
    ) -> EntityRelationship | None:
        return self.session.scalar(
            select(EntityRelationship).where(
                EntityRelationship.subject_type == subject_type,
                EntityRelationship.subject_id == subject_id,
                EntityRelationship.relationship_type == relationship_type,
                EntityRelationship.object_type == object_type,
                EntityRelationship.object_id == object_id,
            )
        )

    def list(
        self,
        *,
        subject_id: str | None = None,
        object_id: str | None = None,
        relationship_type: str | None = None,
        limit: int = 500,
    ) -> list[EntityRelationship]:
        statement = select(EntityRelationship)
        if subject_id:
            statement = statement.where(EntityRelationship.subject_id == subject_id)
        if object_id:
            statement = statement.where(EntityRelationship.object_id == object_id)
        if relationship_type:
            statement = statement.where(EntityRelationship.relationship_type == relationship_type)
        statement = statement.order_by(
            EntityRelationship.review_state,
            EntityRelationship.confidence.desc(),
            EntityRelationship.created_at,
        ).limit(max(1, min(limit, 1000)))
        return list(self.session.scalars(statement))

    def record(self, payload: RelationshipInput) -> EntityRelationship:
        existing = self.find(
            subject_type=payload.subject_type,
            subject_id=payload.subject_id,
            relationship_type=payload.relationship_type,
            object_type=payload.object_type,
            object_id=payload.object_id,
        )
        observed_at = payload.observed_at or datetime.now(UTC)
        if existing is not None:
            if existing.review_state == "candidate":
                existing.confidence = max(existing.confidence, payload.confidence)
                existing.last_seen_at = max(existing.last_seen_at, observed_at)
            self.session.flush()
            return existing
        item = EntityRelationship(
            subject_type=payload.subject_type,
            subject_id=payload.subject_id,
            relationship_type=payload.relationship_type,
            object_type=payload.object_type,
            object_id=payload.object_id,
            confidence=payload.confidence,
            review_state="candidate",
            methodology_version=payload.methodology_version,
            first_seen_at=observed_at,
            last_seen_at=observed_at,
        )
        self.session.add(item)
        self.session.flush()
        return item

    def add_evidence(
        self, relationship_id: str, payload: RelationshipEvidenceInput
    ) -> RelationshipEvidence:
        if self.get(relationship_id) is None:
            raise KeyError(relationship_id)
        canonical_claim = json.dumps(
            payload.structured_claim, sort_keys=True, separators=(",", ":"), default=str
        )
        material = "\x1f".join(
            [
                relationship_id,
                payload.source_type,
                payload.source_url or "",
                payload.source_snapshot_id or "",
                payload.source_observation_id or "",
                payload.observed_at.isoformat(),
                payload.evidence_strength,
                payload.evidence_text or "",
                canonical_claim,
            ]
        ).encode("utf-8")
        fingerprint = hashlib.sha256(material).hexdigest()
        existing = self.session.scalar(
            select(RelationshipEvidence).where(
                RelationshipEvidence.evidence_fingerprint == fingerprint
            )
        )
        if existing is not None:
            return existing
        item = RelationshipEvidence(
            relationship_id=relationship_id,
            evidence_fingerprint=fingerprint,
            source_type=payload.source_type,
            source_url=payload.source_url,
            source_snapshot_id=payload.source_snapshot_id,
            source_observation_id=payload.source_observation_id,
            observed_at=payload.observed_at,
            evidence_strength=payload.evidence_strength,
            evidence_text=payload.evidence_text,
            structured_claim_json=canonical_claim,
        )
        self.session.add(item)
        self.session.flush()
        return item

    def evidence_for(self, relationship_id: str) -> list[RelationshipEvidence]:
        statement = (
            select(RelationshipEvidence)
            .where(RelationshipEvidence.relationship_id == relationship_id)
            .order_by(RelationshipEvidence.observed_at, RelationshipEvidence.id)
        )
        return list(self.session.scalars(statement))

    def review(
        self, relationship_id: str, *, decision: str, reviewer: str
    ) -> EntityRelationship:
        if decision not in self.VALID_DECISIONS:
            raise ValueError("decision must be confirmed or rejected")
        item = self.get(relationship_id)
        if item is None:
            raise KeyError(relationship_id)
        item.review_state = decision
        item.reviewed_by = reviewer
        item.reviewed_at = datetime.now(UTC)
        self.session.flush()
        return item
