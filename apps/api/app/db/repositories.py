from __future__ import annotations

import hashlib
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    Institution,
    MappingEvidence,
    MobileTelemetryEventRecord,
    ReconciliationFinding,
    SourceObservation,
    SourceSnapshot,
)
from app.schemas.mobile import MobileTelemetryEvent
from app.services.message_classifier import classify_features


class InstitutionRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(
        self,
        *,
        legal_name: str,
        trading_name: str | None,
        category: str,
    ) -> Institution:
        entity = Institution(
            legal_name=legal_name,
            trading_name=trading_name,
            category=category,
        )
        self.session.add(entity)
        self.session.flush()
        return entity

    def get(self, institution_id: str) -> Institution | None:
        return self.session.get(Institution, institution_id)

    def list(self, *, limit: int = 100) -> list[Institution]:
        statement = select(Institution).order_by(Institution.legal_name).limit(limit)
        return list(self.session.scalars(statement))


class SourceRepository:
    def __init__(self, session: Session):
        self.session = session

    def record_snapshot(
        self,
        *,
        source_id: str,
        source_url: str,
        sha256: str,
        media_type: str,
        retrieved_at: datetime,
        storage_path: str,
    ) -> SourceSnapshot:
        existing = self.session.scalar(
            select(SourceSnapshot).where(
                SourceSnapshot.source_id == source_id,
                SourceSnapshot.sha256 == sha256,
            )
        )
        if existing is not None:
            return existing
        snapshot = SourceSnapshot(
            source_id=source_id,
            source_url=source_url,
            sha256=sha256,
            media_type=media_type,
            retrieved_at=retrieved_at,
            storage_path=storage_path,
        )
        self.session.add(snapshot)
        self.session.flush()
        return snapshot

    def has_observations(self, snapshot_id: str) -> bool:
        statement = select(SourceObservation.id).where(
            SourceObservation.snapshot_id == snapshot_id
        ).limit(1)
        return self.session.scalar(statement) is not None

    def add_observation(
        self,
        *,
        snapshot_id: str,
        regulator: str,
        external_id: str | None,
        status: str,
        payload_json: str,
    ) -> SourceObservation:
        item = SourceObservation(
            snapshot_id=snapshot_id,
            regulator=regulator,
            external_id=external_id,
            status=status,
            payload_json=payload_json,
        )
        self.session.add(item)
        return item


class ReconciliationRepository:
    VALID_DECISIONS = frozenset({"confirmed", "rejected"})

    def __init__(self, session: Session):
        self.session = session

    def get(self, finding_id: str) -> ReconciliationFinding | None:
        return self.session.get(ReconciliationFinding, finding_id)

    def list(self, *, limit: int = 500) -> list[ReconciliationFinding]:
        statement = (
            select(ReconciliationFinding)
            .order_by(ReconciliationFinding.created_at.desc(), ReconciliationFinding.id)
            .limit(limit)
        )
        return list(self.session.scalars(statement))

    def record(
        self,
        *,
        left_source_key: str,
        right_source_key: str | None,
        finding_type: str,
        confidence: float,
        summary: str,
    ) -> ReconciliationFinding:
        material = "\x1f".join(
            [left_source_key, right_source_key or "", finding_type]
        ).encode("utf-8")
        finding_key = hashlib.sha256(material).hexdigest()
        existing = self.session.scalar(
            select(ReconciliationFinding).where(
                ReconciliationFinding.finding_key == finding_key
            )
        )
        if existing is not None:
            return existing
        finding = ReconciliationFinding(
            finding_key=finding_key,
            left_source_key=left_source_key,
            right_source_key=right_source_key,
            finding_type=finding_type,
            confidence=confidence,
            summary=summary,
            review_state="pending",
        )
        self.session.add(finding)
        self.session.flush()
        return finding

    def resolve(
        self,
        finding_id: str,
        *,
        decision: str,
        reviewer: str,
        institution_id: str | None = None,
    ) -> ReconciliationFinding:
        if decision not in self.VALID_DECISIONS:
            raise ValueError("decision must be confirmed or rejected")
        finding = self.get(finding_id)
        if finding is None:
            raise KeyError(finding_id)
        finding.review_state = decision
        finding.reviewed_by = reviewer
        finding.reviewed_at = datetime.now(UTC)
        finding.resolved_institution_id = institution_id if decision == "confirmed" else None
        self.session.flush()
        return finding


class MappingEvidenceRepository:
    def __init__(self, session: Session):
        self.session = session

    def record(
        self,
        *,
        kind: str,
        evidence_fingerprint: str,
        app_package: str | None = None,
        sender_identifier: str | None = None,
    ) -> MappingEvidence:
        existing = self.session.scalar(
            select(MappingEvidence).where(
                MappingEvidence.evidence_fingerprint == evidence_fingerprint
            )
        )
        if existing is not None:
            return existing
        item = MappingEvidence(
            kind=kind,
            app_package=app_package,
            sender_identifier=sender_identifier,
            evidence_fingerprint=evidence_fingerprint,
            verification_state="unverified",
        )
        self.session.add(item)
        self.session.flush()
        return item


class MobileTelemetryRepository:
    def __init__(self, session: Session):
        self.session = session

    def add(self, event: MobileTelemetryEvent) -> MobileTelemetryEventRecord:
        existing = self.session.get(MobileTelemetryEventRecord, event.event_id)
        if existing is not None:
            return existing
        server_result = classify_features(event.features)
        item = MobileTelemetryEventRecord(
            id=event.event_id,
            client_hash=hashlib.sha256(event.client_id.encode("utf-8")).hexdigest(),
            source_kind=event.source_kind,
            app_version=event.app_version,
            model_version=event.model_version,
            predicted_label=event.predicted_label,
            server_label=server_result.label,
            confidence=event.confidence,
            user_label=event.user_label,
            features_json=event.features.model_dump_json(),
        )
        self.session.add(item)
        self.session.flush()
        return item

    def label(self, event_id: str, label: str) -> MobileTelemetryEventRecord:
        item = self.session.get(MobileTelemetryEventRecord, event_id)
        if item is None:
            raise KeyError(event_id)
        item.user_label = label
        self.session.flush()
        return item

    def recent(self, *, limit: int = 200) -> list[MobileTelemetryEventRecord]:
        statement = (
            select(MobileTelemetryEventRecord)
            .order_by(MobileTelemetryEventRecord.created_at.desc())
            .limit(max(1, min(limit, 1000)))
        )
        return list(self.session.scalars(statement))
