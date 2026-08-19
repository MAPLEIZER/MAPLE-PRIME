from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.db.models import (
    AppOwnershipLink,
    AppStoreObservation,
    Institution,
    MappingEvidence,
    MarketplaceApp,
    MobileTelemetryEventRecord,
    ReconciliationFinding,
    SourceObservation,
    SourceSnapshot,
)
from app.schemas.apps import PlayAppImportItem
from app.schemas.mobile import MobileTelemetryEvent
from app.services.app_registry import domain_from_url, email_domain, score_ownership_candidate
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


class AppRegistryRepository:
    VALID_REVIEW_DECISIONS = frozenset({"confirmed", "rejected"})

    def __init__(self, session: Session):
        self.session = session

    def get(self, app_id: str) -> MarketplaceApp | None:
        return self.session.get(MarketplaceApp, app_id)

    def get_link(self, link_id: str) -> AppOwnershipLink | None:
        return self.session.get(AppOwnershipLink, link_id)

    def ingest_play(self, item: PlayAppImportItem) -> MarketplaceApp:
        app = self.session.scalar(
            select(MarketplaceApp).where(
                MarketplaceApp.store == item.store,
                MarketplaceApp.package_name == item.package_name,
            )
        )
        if app is None:
            app = MarketplaceApp(
                store=item.store,
                package_name=item.package_name,
                loan_relevance="candidate",
                first_seen_at=item.observed_at,
                last_seen_at=item.observed_at,
            )
            self.session.add(app)
            self.session.flush()
        else:
            if item.observed_at < app.first_seen_at:
                app.first_seen_at = item.observed_at
            if item.observed_at > app.last_seen_at:
                app.last_seen_at = item.observed_at

        payload = item.model_dump(mode="json")
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        observation_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        existing = self.session.scalar(
            select(AppStoreObservation.id).where(
                AppStoreObservation.observation_hash == observation_hash
            )
        )
        if existing is None:
            support_domain = email_domain(item.support_email or "")
            observation = AppStoreObservation(
                app_id=app.id,
                observation_hash=observation_hash,
                source_provider=item.source_provider,
                source_url=item.source_url,
                observed_at=item.observed_at,
                app_name=item.app_name,
                developer_name=item.developer_name,
                developer_id=item.developer_id,
                support_email=item.support_email,
                email_domain=support_domain,
                developer_website=item.developer_website,
                developer_domain=domain_from_url(item.developer_website),
                privacy_policy_url=item.privacy_policy_url,
                store_url=item.store_url,
                category=item.category,
                installs=item.installs,
                payload_json=canonical,
            )
            self.session.add(observation)
            self.session.flush()
        return app

    def observations(self, app_id: str, *, limit: int = 100) -> list[AppStoreObservation]:
        statement = (
            select(AppStoreObservation)
            .where(AppStoreObservation.app_id == app_id)
            .order_by(AppStoreObservation.observed_at.desc(), AppStoreObservation.id)
            .limit(max(1, min(limit, 1000)))
        )
        return list(self.session.scalars(statement))

    def latest_observation(self, app_id: str) -> AppStoreObservation | None:
        statement = (
            select(AppStoreObservation)
            .where(AppStoreObservation.app_id == app_id)
            .order_by(AppStoreObservation.observed_at.desc(), AppStoreObservation.id.desc())
            .limit(1)
        )
        return self.session.scalar(statement)

    @staticmethod
    def _dedupe_apps(items: list[MarketplaceApp]) -> list[MarketplaceApp]:
        seen: set[str] = set()
        result: list[MarketplaceApp] = []
        for item in items:
            if item.id not in seen:
                seen.add(item.id)
                result.append(item)
        return result

    def find_by_email(self, value: str) -> list[MarketplaceApp]:
        canonical = value.strip().lower()
        statement = (
            select(MarketplaceApp)
            .join(AppStoreObservation, AppStoreObservation.app_id == MarketplaceApp.id)
            .where(func.lower(AppStoreObservation.support_email) == canonical)
            .order_by(MarketplaceApp.package_name)
        )
        return self._dedupe_apps(list(self.session.scalars(statement)))

    def find_by_domain(self, value: str) -> list[MarketplaceApp]:
        domain = value.strip().lower().removeprefix("www.").strip(".")
        statement = (
            select(MarketplaceApp)
            .join(AppStoreObservation, AppStoreObservation.app_id == MarketplaceApp.id)
            .where(
                or_(
                    func.lower(AppStoreObservation.email_domain) == domain,
                    func.lower(AppStoreObservation.developer_domain) == domain,
                )
            )
            .order_by(MarketplaceApp.package_name)
        )
        return self._dedupe_apps(list(self.session.scalars(statement)))

    def list_apps(self, *, limit: int = 500) -> list[MarketplaceApp]:
        statement = (
            select(MarketplaceApp)
            .order_by(MarketplaceApp.last_seen_at.desc(), MarketplaceApp.package_name)
            .limit(max(1, min(limit, 1000)))
        )
        return list(self.session.scalars(statement))

    def links_for_app(self, app_id: str) -> list[AppOwnershipLink]:
        statement = (
            select(AppOwnershipLink)
            .where(AppOwnershipLink.app_id == app_id)
            .order_by(AppOwnershipLink.confidence.desc(), AppOwnershipLink.created_at)
        )
        return list(self.session.scalars(statement))

    def _latest_cbk_emails(self, institution_id: str) -> tuple[str, ...]:
        observation = self.session.scalar(
            select(SourceObservation)
            .join(SourceSnapshot, SourceObservation.snapshot_id == SourceSnapshot.id)
            .where(
                SourceObservation.institution_id == institution_id,
                SourceSnapshot.source_id == "cbk_dcp",
            )
            .order_by(SourceSnapshot.retrieved_at.desc(), SourceSnapshot.id.desc())
            .limit(1)
        )
        if observation is None:
            return ()
        try:
            payload = json.loads(observation.payload_json)
        except (TypeError, json.JSONDecodeError):
            return ()
        return tuple(
            str(value).strip().lower()
            for value in (payload.get("emails") or [])
            if str(value).strip()
        )

    def generate_candidates(self, app_id: str) -> list[AppOwnershipLink]:
        app = self.get(app_id)
        observation = self.latest_observation(app_id)
        if app is None or observation is None:
            raise KeyError(app_id)
        schema = PlayAppImportItem.model_validate(json.loads(observation.payload_json))
        links: list[AppOwnershipLink] = []
        for institution in self.session.scalars(select(Institution).order_by(Institution.legal_name)):
            score = score_ownership_candidate(
                schema,
                institution_legal_name=institution.legal_name,
                institution_trading_name=institution.trading_name,
                institution_website=institution.website,
                institution_public_emails=self._latest_cbk_emails(institution.id),
            )
            if score.confidence < 0.35 or not score.signals:
                continue
            existing = self.session.scalar(
                select(AppOwnershipLink).where(
                    AppOwnershipLink.app_id == app.id,
                    AppOwnershipLink.institution_id == institution.id,
                )
            )
            signals_json = json.dumps(list(score.signals), separators=(",", ":"))
            if existing is None:
                existing = AppOwnershipLink(
                    app_id=app.id,
                    institution_id=institution.id,
                    confidence=score.confidence,
                    signals_json=signals_json,
                    review_state="candidate",
                )
                self.session.add(existing)
                self.session.flush()
            elif existing.review_state == "candidate":
                existing.confidence = score.confidence
                existing.signals_json = signals_json
            links.append(existing)
        return sorted(links, key=lambda item: (-item.confidence, item.institution_id))

    def review_link(self, link_id: str, *, decision: str, reviewer: str) -> AppOwnershipLink:
        if decision not in self.VALID_REVIEW_DECISIONS:
            raise ValueError("decision must be confirmed or rejected")
        link = self.get_link(link_id)
        if link is None:
            raise KeyError(link_id)
        link.review_state = decision
        link.reviewed_by = reviewer
        link.reviewed_at = datetime.now(UTC)
        self.session.flush()
        return link
