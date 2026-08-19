from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.repositories import InstitutionRepository, MappingEvidenceRepository


def _session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def test_institution_repository_round_trip() -> None:
    with _session() as session:
        repo = InstitutionRepository(session)
        created = repo.create(
            legal_name="Example Credit Limited",
            trading_name="Example Credit",
            category="digital_credit_provider",
        )
        session.commit()
        loaded = repo.get(created.id)
        assert loaded is not None
        assert loaded.legal_name == "Example Credit Limited"
        assert repo.list(limit=10)[0].id == created.id


def test_mapping_evidence_is_unverified_by_default_and_deduplicated() -> None:
    with _session() as session:
        repo = MappingEvidenceRepository(session)
        first = repo.record(
            kind="app_package",
            app_package="com.example.credit",
            evidence_fingerprint="a" * 64,
        )
        second = repo.record(
            kind="app_package",
            app_package="com.example.credit",
            evidence_fingerprint="a" * 64,
        )
        session.commit()
        assert first.id == second.id
        assert first.verification_state == "unverified"
        assert first.institution_id is None
