from datetime import UTC, datetime
from decimal import Decimal

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.api.local_actions import require_pricing_action
from app.db.base import Base
from app.db.models import MarketplaceApp
from app.db.pricing_repository import LoanPricingRepository
from app.schemas.pricing import LoanTermObservationInput
from app.services.pricing import calculate_loan_cost


def _pricing_input(app_id: str, **updates: object) -> LoanTermObservationInput:
    payload: dict[str, object] = {
        "app_id": app_id,
        "source_type": "public_disclosure",
        "source_provider": "fixture",
        "source_url": "https://example.co.ke/loan-terms",
        "observed_at": datetime(2026, 8, 19, tzinfo=UTC),
        "currency": "KES",
        "amount_received": Decimal("5000.00"),
        "total_repayment": Decimal("6050.00"),
        "term_days": 30,
        "advertised_interest_rate_percent": Decimal("10.00"),
        "interest_amount": Decimal("500.00"),
        "processing_fee": Decimal("250.00"),
        "service_fee": Decimal("200.00"),
        "insurance_fee": Decimal("100.00"),
    }
    payload.update(updates)
    return LoanTermObservationInput.model_validate(payload)


def test_effective_cost_uses_amount_received_and_total_repayment_not_advertised_rate() -> None:
    result = calculate_loan_cost(
        amount_received=Decimal("5000.00"),
        total_repayment=Decimal("6050.00"),
        interest_amount=Decimal("500.00"),
        mandatory_fees=(Decimal("250.00"), Decimal("200.00"), Decimal("100.00")),
    )

    assert result.effective_cost_amount == Decimal("1050.00")
    assert result.effective_cost_percent == Decimal("21.00")
    assert result.known_cost_amount == Decimal("1050.00")
    assert result.unexplained_cost_amount == Decimal("0.00")


def test_unexplained_cost_is_visible_when_repayment_exceeds_known_line_items() -> None:
    result = calculate_loan_cost(
        amount_received=Decimal("5000.00"),
        total_repayment=Decimal("6050.00"),
        interest_amount=Decimal("500.00"),
        mandatory_fees=(Decimal("250.00"),),
    )

    assert result.effective_cost_amount == Decimal("1050.00")
    assert result.known_cost_amount == Decimal("750.00")
    assert result.unexplained_cost_amount == Decimal("300.00")


def test_pricing_schema_rejects_impossible_or_inconsistent_terms() -> None:
    with pytest.raises(ValidationError):
        _pricing_input("app-1", total_repayment=Decimal("4999.00"))

    with pytest.raises(ValidationError):
        _pricing_input(
            "app-1",
            total_repayment=Decimal("5200.00"),
            interest_amount=Decimal("500.00"),
        )

    with pytest.raises(ValidationError):
        _pricing_input("app-1", source_url="http://example.co.ke/loan-terms")


def test_pricing_repository_is_append_only_and_deduplicates_identical_evidence() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        app = MarketplaceApp(
            store="google_play",
            package_name="ke.co.example.loan",
            loan_relevance="candidate",
            first_seen_at=datetime(2026, 8, 18, tzinfo=UTC),
            last_seen_at=datetime(2026, 8, 19, tzinfo=UTC),
        )
        session.add(app)
        session.flush()

        repository = LoanPricingRepository(session)
        first = repository.record(_pricing_input(app.id))
        duplicate = repository.record(_pricing_input(app.id))
        later = repository.record(
            _pricing_input(
                app.id,
                observed_at=datetime(2026, 8, 20, tzinfo=UTC),
                total_repayment=Decimal("6100.00"),
            )
        )

        assert first.id == duplicate.id
        assert later.id != first.id
        records = repository.list(app_id=app.id)
        assert [record.total_repayment for record in records] == [
            Decimal("6100.00"),
            Decimal("6050.00"),
        ]
        assert records[0].effective_cost_percent == Decimal("22.0000")


def test_pricing_write_requires_a_dedicated_local_action() -> None:
    with pytest.raises(HTTPException):
        require_pricing_action("import_apps")
    assert require_pricing_action("record_pricing") == "record_pricing"
