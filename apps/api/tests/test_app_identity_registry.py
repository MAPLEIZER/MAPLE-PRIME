import json
from datetime import UTC, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.models import Institution, SourceObservation, SourceSnapshot
from app.db.repositories import AppRegistryRepository
from app.schemas.apps import PlayAppImportItem
from app.services.app_registry import corporate_domain_from_email, score_ownership_candidate


def test_public_support_email_domain_is_normalized_but_generic_mail_is_not_ownership_signal() -> None:
    assert corporate_domain_from_email("Support@Example.CO.KE") == "example.co.ke"
    assert corporate_domain_from_email("loanapp@gmail.com") is None
    assert corporate_domain_from_email("help@yahoo.com") is None


def test_ownership_candidate_requires_evidence_and_never_auto_confirms() -> None:
    app = PlayAppImportItem(
        package_name="ke.co.example.loan",
        app_name="Example Cash",
        developer_name="Example Credit Limited",
        support_email="support@example.co.ke",
        developer_website="https://example.co.ke",
        store_url="https://play.google.com/store/apps/details?id=ke.co.example.loan",
        source_provider="fixture",
        source_url="https://play.google.com/store/apps/details?id=ke.co.example.loan",
        observed_at=datetime(2026, 8, 19, tzinfo=UTC),
    )
    score = score_ownership_candidate(
        app,
        institution_legal_name="Example Credit Limited",
        institution_trading_name="Example Cash",
        institution_website="https://example.co.ke",
    )
    assert score.confidence >= 0.8
    assert "website_domain_exact" in score.signals
    assert score.review_state == "candidate"


def test_registry_upserts_app_identity_but_keeps_append_only_observations_and_reverse_indexes() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        institution = Institution(
            legal_name="Example Credit Limited",
            trading_name="Example Cash",
            category="digital_credit_provider",
            website="https://example.co.ke",
        )
        session.add(institution)
        repository = AppRegistryRepository(session)
        first = PlayAppImportItem(
            package_name="ke.co.example.loan",
            app_name="Example Cash",
            developer_name="Example Credit Limited",
            support_email="support@example.co.ke",
            developer_website="https://example.co.ke",
            store_url="https://play.google.com/store/apps/details?id=ke.co.example.loan",
            source_provider="fixture",
            source_url="https://play.google.com/store/apps/details?id=ke.co.example.loan",
            observed_at=datetime(2026, 8, 18, tzinfo=UTC),
        )
        second = first.model_copy(update={"app_name": "Example Cash Loans", "observed_at": datetime(2026, 8, 19, tzinfo=UTC)})
        app = repository.ingest_play(first)
        again = repository.ingest_play(second)
        assert app.id == again.id
        assert len(repository.observations(app.id)) == 2
        assert [item.package_name for item in repository.find_by_email("SUPPORT@example.co.ke")] == ["ke.co.example.loan"]
        assert [item.package_name for item in repository.find_by_domain("example.co.ke")] == ["ke.co.example.loan"]

        links = repository.generate_candidates(app.id)
        assert len(links) == 1
        assert links[0].institution_id == institution.id
        assert links[0].review_state == "candidate"
        assert links[0].confidence >= 0.8


def test_exact_cbk_published_email_can_surface_obfuscated_play_identity_without_auto_confirming() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        institution = Institution(
            legal_name="Known Credit Limited",
            trading_name="Known Credit",
            category="digital_credit_provider",
            website=None,
        )
        session.add(institution)
        session.flush()
        snapshot = SourceSnapshot(
            source_id="cbk_dcp",
            source_url="https://www.centralbank.go.ke/dcp.pdf",
            sha256="b" * 64,
            media_type="application/pdf",
            retrieved_at=datetime(2026, 8, 19, tzinfo=UTC),
            storage_path="snapshots/b.pdf",
        )
        session.add(snapshot)
        session.flush()
        session.add(
            SourceObservation(
                snapshot_id=snapshot.id,
                institution_id=institution.id,
                regulator="CBK",
                external_id="7",
                status="licensed",
                payload_json=json.dumps(
                    {
                        "sequence": 7,
                        "legal_name": "Known Credit Limited",
                        "trading_name": "Known Credit",
                        "emails": ["loans@knowncredit.co.ke"],
                    }
                ),
            )
        )
        repository = AppRegistryRepository(session)
        app = repository.ingest_play(
            PlayAppImportItem(
                package_name="com.generic.publisher.fastmoney",
                app_name="Fast Money",
                developer_name="Mobile Services Studio",
                support_email="LOANS@KNOWNCREDIT.CO.KE",
                store_url="https://play.google.com/store/apps/details?id=com.generic.publisher.fastmoney",
                source_provider="fixture",
                source_url="https://play.google.com/store/apps/details?id=com.generic.publisher.fastmoney",
                observed_at=datetime(2026, 8, 19, tzinfo=UTC),
            )
        )
        links = repository.generate_candidates(app.id)
        assert len(links) == 1
        assert links[0].institution_id == institution.id
        assert links[0].review_state == "candidate"
        assert links[0].confidence >= 0.55
        assert "cbk_published_email_exact" in json.loads(links[0].signals_json)
