from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models import new_id


class LoanTermObservation(Base):
    __tablename__ = "loan_term_observations"
    __table_args__ = (
        UniqueConstraint("observation_hash", name="uq_loan_term_observation_hash"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    app_id: Mapped[str] = mapped_column(ForeignKey("marketplace_apps.id"), index=True)
    institution_id: Mapped[str | None] = mapped_column(
        ForeignKey("institutions.id"), nullable=True, index=True
    )
    observation_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    source_type: Mapped[str] = mapped_column(String(40), index=True)
    source_provider: Mapped[str] = mapped_column(String(120), index=True)
    source_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    currency: Mapped[str] = mapped_column(String(3), default="KES", index=True)
    amount_received: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    total_repayment: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    term_days: Mapped[int] = mapped_column()
    advertised_interest_rate_percent: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 4), nullable=True
    )
    advertised_rate_basis: Mapped[str] = mapped_column(String(20), default="unspecified")
    interest_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0.00"))
    processing_fee: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0.00"))
    service_fee: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0.00"))
    insurance_fee: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0.00"))
    disbursement_fee: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0.00"))
    other_mandatory_fees: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), default=Decimal("0.00")
    )
    disclosed_late_fee: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0.00"))
    disclosed_rollover_fee: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), default=Decimal("0.00")
    )
    effective_cost_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    effective_cost_percent: Mapped[Decimal] = mapped_column(Numeric(12, 4))
    known_cost_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    unexplained_cost_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    payload_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), index=True
    )
