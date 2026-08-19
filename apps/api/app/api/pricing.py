from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.local_actions import require_pricing_action
from app.db.pricing_repository import LoanPricingRepository
from app.db.session import get_session
from app.schemas.pricing import LoanTermObservationInput

router = APIRouter(prefix="/api/v1/pricing", tags=["loan pricing intelligence"])
DbSession = Annotated[Session, Depends(get_session)]


def _decimal(value: Decimal | None) -> str | None:
    return None if value is None else format(value, "f")


def _serialize(record) -> dict[str, object]:
    return {
        "id": record.id,
        "app_id": record.app_id,
        "institution_id": record.institution_id,
        "source_type": record.source_type,
        "source_provider": record.source_provider,
        "source_url": record.source_url,
        "observed_at": record.observed_at.isoformat(),
        "currency": record.currency,
        "amount_received": _decimal(record.amount_received),
        "total_repayment": _decimal(record.total_repayment),
        "term_days": record.term_days,
        "advertised_interest_rate_percent": _decimal(record.advertised_interest_rate_percent),
        "advertised_rate_basis": record.advertised_rate_basis,
        "interest_amount": _decimal(record.interest_amount),
        "processing_fee": _decimal(record.processing_fee),
        "service_fee": _decimal(record.service_fee),
        "insurance_fee": _decimal(record.insurance_fee),
        "disbursement_fee": _decimal(record.disbursement_fee),
        "other_mandatory_fees": _decimal(record.other_mandatory_fees),
        "disclosed_late_fee": _decimal(record.disclosed_late_fee),
        "disclosed_rollover_fee": _decimal(record.disclosed_rollover_fee),
        "effective_cost_amount": _decimal(record.effective_cost_amount),
        "effective_cost_percent": _decimal(record.effective_cost_percent),
        "known_cost_amount": _decimal(record.known_cost_amount),
        "unexplained_cost_amount": _decimal(record.unexplained_cost_amount),
    }


@router.get("")
def list_pricing(
    session: DbSession,
    app_id: str | None = Query(default=None, max_length=36),
    institution_id: str | None = Query(default=None, max_length=36),
    limit: int = Query(default=500, ge=1, le=1000),
) -> list[dict[str, object]]:
    repository = LoanPricingRepository(session)
    return [
        _serialize(item)
        for item in repository.list(app_id=app_id, institution_id=institution_id, limit=limit)
    ]


@router.get("/summary")
def pricing_summary(
    session: DbSession,
    app_id: str | None = Query(default=None, max_length=36),
) -> dict[str, object]:
    records = LoanPricingRepository(session).list(app_id=app_id, limit=1000)
    app_ids = {record.app_id for record in records}
    latest = records[0] if records and app_id is not None else None
    return {
        "observations": len(records),
        "apps_with_pricing": len(app_ids),
        "latest_effective_cost_percent": (
            _decimal(latest.effective_cost_percent) if latest is not None else None
        ),
        "latest_term_days": latest.term_days if latest is not None else None,
    }


@router.get("/export")
def export_pricing(session: DbSession) -> dict[str, object]:
    records = LoanPricingRepository(session).list(limit=1000)
    return {
        "schema_version": "kdr-loan-pricing-v1",
        "generated_at": datetime.now(UTC).isoformat(),
        "methodology_note": (
            "effective_cost_percent is the cost over the observed loan term relative to amount "
            "actually received. It is not APR. Late and rollover fees are disclosed separately "
            "and excluded from baseline effective cost unless they are part of total repayment."
        ),
        "records": [_serialize(item) for item in records],
    }


@router.post("", dependencies=[Depends(require_pricing_action)])
def record_pricing(
    payload: LoanTermObservationInput,
    session: DbSession,
) -> dict[str, object]:
    repository = LoanPricingRepository(session)
    try:
        record = repository.record(payload)
        session.commit()
    except KeyError as exc:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="app or institution not found",
        ) from exc
    except Exception:
        session.rollback()
        raise
    return _serialize(record)
