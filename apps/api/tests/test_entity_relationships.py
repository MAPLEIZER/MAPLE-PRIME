import json
from datetime import UTC, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.models import Institution, MarketplaceApp
from app.db.relationship_repository import EntityRelationshipRepository
from app.schemas.relationships import RelationshipEvidenceInput, RelationshipInput


def test_relationship_graph_keeps_relationship_type_distinct_from_entity_identity() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        institution = Institution(
            legal_name="Example Credit Limited",
            trading_name="Example Cash",
            category="digital_credit_provider",
        )
        app = MarketplaceApp(
            store="google_play",
            package_name="ke.co.example.cash",
            loan_relevance="candidate",
            first_seen_at=datetime(2026, 8, 19, tzinfo=UTC),
            last_seen_at=datetime(2026, 8, 19, tzinfo=UTC),
        )
        session.add_all([institution, app])
        session.flush()

        repo = EntityRelationshipRepository(session)
        published = repo.record(
            RelationshipInput(
                subject_type="marketplace_app",
                subject_id=app.id,
                relationship_type="published_by",
                object_type="institution",
                object_id=institution.id,
                confidence=0.72,
            )
        )
        operated = repo.record(
            RelationshipInput(
                subject_type="marketplace_app",
                subject_id=app.id,
                relationship_type="operated_by",
                object_type="institution",
                object_id=institution.id,
                confidence=0.88,
            )
        )

        assert published.id != operated.id
        assert published.relationship_type == "published_by"
        assert operated.relationship_type == "operated_by"
        assert published.review_state == "candidate"


def test_relationship_evidence_is_append_only_and_review_does_not_mutate_evidence() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        app = MarketplaceApp(
            store="google_play",
            package_name="ke.co.example.cash",
            loan_relevance="candidate",
            first_seen_at=datetime(2026, 8, 19, tzinfo=UTC),
            last_seen_at=datetime(2026, 8, 19, tzinfo=UTC),
        )
        institution = Institution(
            legal_name="Example Credit Limited",
            trading_name="Example Cash",
            category="digital_credit_provider",
        )
        session.add_all([app, institution])
        session.flush()
        repo = EntityRelationshipRepository(session)
        relationship = repo.record(
            RelationshipInput(
                subject_type="marketplace_app",
                subject_id=app.id,
                relationship_type="operated_by",
                object_type="institution",
                object_id=institution.id,
                confidence=0.91,
            )
        )
        evidence = repo.add_evidence(
            relationship.id,
            RelationshipEvidenceInput(
                source_type="privacy_policy",
                source_url="https://example.co.ke/privacy",
                observed_at=datetime(2026, 8, 19, tzinfo=UTC),
                evidence_strength="very_strong",
                structured_claim={"legal_operator": "Example Credit Limited"},
                evidence_text="Service operated by Example Credit Limited",
            ),
        )
        fingerprint = evidence.evidence_fingerprint
        payload_before = evidence.structured_claim_json

        reviewed = repo.review(relationship.id, decision="confirmed", reviewer="local_user")
        evidence_after = repo.evidence_for(relationship.id)[0]

        assert reviewed.review_state == "confirmed"
        assert evidence_after.evidence_fingerprint == fingerprint
        assert evidence_after.structured_claim_json == payload_before
        assert json.loads(evidence_after.structured_claim_json)["legal_operator"] == "Example Credit Limited"


def test_confirmed_relationship_can_express_parent_and_beneficial_owner_without_overloading_app_owner() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        lender = Institution(
            legal_name="Example Credit Limited",
            category="digital_credit_provider",
        )
        parent = Institution(
            legal_name="Example Holdings Limited",
            category="company",
        )
        session.add_all([lender, parent])
        session.flush()
        repo = EntityRelationshipRepository(session)

        parent_link = repo.record(
            RelationshipInput(
                subject_type="institution",
                subject_id=lender.id,
                relationship_type="subsidiary_of",
                object_type="institution",
                object_id=parent.id,
                confidence=0.95,
            )
        )
        beneficial = repo.record(
            RelationshipInput(
                subject_type="institution",
                subject_id=parent.id,
                relationship_type="beneficially_owned_by",
                object_type="external_entity",
                object_id="brs-person-or-entity-ref",
                confidence=0.95,
            )
        )

        assert parent_link.relationship_type == "subsidiary_of"
        assert beneficial.object_type == "external_entity"
        assert beneficial.review_state == "candidate"
