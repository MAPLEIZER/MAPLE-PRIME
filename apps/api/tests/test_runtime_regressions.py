from datetime import datetime

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.models import AppOwnershipLink, AppStoreObservation, Institution, MarketplaceApp
from app.db.relationship_repository import EntityRelationshipRepository
from app.db.session import configure_sqlite_connection
from app.services import regulatory_reconciliation
from app.services.cbk_dcp import DcpDirectoryRecord
from app.services.odpc_registry import OdpcHandlerRecord
from app.services.regulatory_reconciliation import reconcile_cbk_odpc
from app.services.relationship_backfill import sync_app_ownership_relationships


def _cbk(name: str, trading: str | None = None, sequence: int = 1) -> DcpDirectoryRecord:
    return DcpDirectoryRecord(
        sequence=sequence,
        legal_name=name,
        trading_name=trading,
        website=None,
        emails=(),
        phones=(),
        postal_address=None,
        physical_address=None,
        licensed_date=None,
    )


def _odpc(name: str, registration: str, sequence: int = 1) -> OdpcHandlerRecord:
    return OdpcHandlerRecord(
        sequence=sequence,
        name=name,
        handler_type="data_controller",
        registration_number=registration,
        county=None,
        country="Kenya",
        status="active",
        status_as_at=None,
    )


def test_exact_reconciliation_uses_index_without_fuzzy_scanning_every_odpc_row(monkeypatch: pytest.MonkeyPatch) -> None:
    cbk = _cbk("Alpha Credit Limited")
    odpc = [_odpc(f"Unrelated Handler {index}", f"ODPC-{index}", index) for index in range(500)]
    odpc.append(_odpc("Alpha Credit Ltd", "ODPC-ALPHA", 999))

    class ForbiddenSequenceMatcher:
        def __init__(self, *args: object, **kwargs: object) -> None:
            raise AssertionError("exact-name reconciliation must not run a full fuzzy scan")

    monkeypatch.setattr(regulatory_reconciliation, "SequenceMatcher", ForbiddenSequenceMatcher)
    findings = reconcile_cbk_odpc([cbk], odpc)

    assert len(findings) == 1
    assert findings[0].review_state == "confirmed"
    assert findings[0].odpc_registration_number == "ODPC-ALPHA"
    assert findings[0].match_basis == "normalized_legal_name_exact"


def test_sqlite_connections_enable_wal_and_wait_for_short_write_contention(tmp_path) -> None:
    path = tmp_path / "kdr.sqlite3"
    engine = create_engine(
        f"sqlite:///{path}",
        connect_args={"check_same_thread": False, "timeout": 30},
    )
    configure_sqlite_connection(engine)
    with engine.connect() as connection:
        journal_mode = connection.execute(text("PRAGMA journal_mode")).scalar_one().lower()
        busy_timeout = int(connection.execute(text("PRAGMA busy_timeout")).scalar_one())
        foreign_keys = int(connection.execute(text("PRAGMA foreign_keys")).scalar_one())

    assert journal_mode == "wal"
    assert busy_timeout >= 30_000
    assert foreign_keys == 1


def test_relationship_backfill_accepts_sqlite_naive_timestamps_on_repeated_runs() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        naive = datetime(2026, 8, 19, 16, 22, 41)
        app = MarketplaceApp(
            store="google_play",
            package_name="ke.co.alpha.cash",
            loan_relevance="candidate",
            first_seen_at=naive,
            last_seen_at=naive,
        )
        institution = Institution(
            legal_name="Alpha Credit Limited",
            trading_name="Alpha Cash",
            category="digital_credit_provider",
        )
        session.add_all([app, institution])
        session.flush()
        observation = AppStoreObservation(
            app_id=app.id,
            observation_hash="a" * 64,
            source_provider="fixture",
            source_url="https://example.test/app",
            observed_at=naive,
            app_name="Alpha Cash",
            developer_name="Alpha Credit Limited",
            developer_id=None,
            support_email="support@alpha.test",
            email_domain="alpha.test",
            developer_website="https://alpha.test",
            developer_domain="alpha.test",
            privacy_policy_url="https://alpha.test/privacy",
            store_url="https://play.google.com/store/apps/details?id=ke.co.alpha.cash",
            category="Finance",
            installs="1,000+",
            payload_json="{}",
        )
        link = AppOwnershipLink(
            app_id=app.id,
            institution_id=institution.id,
            confidence=0.95,
            signals_json='["website_domain_exact"]',
            review_state="candidate",
            created_at=naive,
        )
        session.add_all([observation, link])
        session.flush()

        assert sync_app_ownership_relationships(session, app_id=app.id) == 1
        session.commit()
        session.expire_all()

        # SQLite returns DateTime values without tzinfo. A repeated discovery run
        # must reattach UTC before Pydantic validation or datetime comparison.
        assert sync_app_ownership_relationships(session, app_id=app.id) == 1
        repository = EntityRelationshipRepository(session)
        relationships = repository.list(subject_id=app.id)
        assert len(relationships) == 1
        evidence = repository.evidence_for(relationships[0].id)
        assert len(evidence) == 1
