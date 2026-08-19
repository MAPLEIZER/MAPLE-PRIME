from datetime import UTC, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.models import Institution
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
