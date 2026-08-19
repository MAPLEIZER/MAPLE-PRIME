from __future__ import annotations

import hashlib
import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Institution, MarketplaceApp
from app.db.pricing_models import LoanTermObservation
from app.schemas.pricing import LoanTermObservationInput
from app.services.pricing import calculate_loan_cost


class LoanPricingRepository:
    def __init__(self, session: Session):
        self.session = session

    def get(self, observation_id: str) -> LoanTermObservation | None:
        return self.session.get(LoanTermObservation, observation_id)

    def record(self, item: LoanTermObservationInput) -> LoanTermObservation:
        if self.session.get(MarketplaceApp, item.app_id) is None:
            raise KeyError(item.app_id)
        if item.institution_id is not None and self.session.get(Institution, item.institution_id) is None:
            raise KeyError(item.institution_id)

        payload = item.model_dump(mode="json")
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        observation_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        existing = self.session.scalar(
            select(LoanTermObservation).where(
                LoanTermObservation.observation_hash == observation_hash
            )
        )
        if existing is not None:
            return existing

        breakdown = calculate_loan_cost(
            amount_received=item.amount_received,
            total_repayment=item.total_repayment,
            interest_amount=item.interest_amount,
            mandatory_fees=(
                item.processing_fee,
                item.service_fee,
                item.insurance_fee,
                item.disbursement_fee,
                item.other_mandatory_fees,
            ),
        )
        record = LoanTermObservation(
            app_id=item.app_id,
            institution_id=item.institution_id,
            observation_hash=observation_hash,
            source_type=item.source_type,
            source_provider=item.source_provider,
            source_url=item.source_url,
            observed_at=item.observed_at,
            currency=item.currency,
            amount_received=item.amount_received,
            total_repayment=item.total_repayment,
            term_days=item.term_days,
            advertised_interest_rate_percent=item.advertised_interest_rate_percent,
            advertised_rate_basis=item.advertised_rate_basis,
            interest_amount=item.interest_amount,
            processing_fee=item.processing_fee,
            service_fee=item.service_fee,
            insurance_fee=item.insurance_fee,
            disbursement_fee=item.disbursement_fee,
            other_mandatory_fees=item.other_mandatory_fees,
            disclosed_late_fee=item.disclosed_late_fee,
            disclosed_rollover_fee=item.disclosed_rollover_fee,
            effective_cost_amount=breakdown.effective_cost_amount,
            effective_cost_percent=breakdown.effective_cost_percent,
            known_cost_amount=breakdown.known_cost_amount,
            unexplained_cost_amount=breakdown.unexplained_cost_amount,
            payload_json=canonical,
        )
        self.session.add(record)
        self.session.flush()
        return record

    def list(
        self,
        *,
        app_id: str | None = None,
        institution_id: str | None = None,
        limit: int = 500,
    ) -> list[LoanTermObservation]:
        statement = select(LoanTermObservation)
        if app_id is not None:
            statement = statement.where(LoanTermObservation.app_id == app_id)
        if institution_id is not None:
            statement = statement.where(LoanTermObservation.institution_id == institution_id)
        statement = statement.order_by(
            LoanTermObservation.observed_at.desc(), LoanTermObservation.id.desc()
        ).limit(max(1, min(limit, 1000)))
        return list(self.session.scalars(statement))
