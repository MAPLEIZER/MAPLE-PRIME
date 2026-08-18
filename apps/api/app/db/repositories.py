from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Institution, MappingEvidence


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
