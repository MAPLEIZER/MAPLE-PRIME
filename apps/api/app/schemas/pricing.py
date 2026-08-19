from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import Literal
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator, model_validator

_MONEY = Decimal("0.01")
_RATE = Decimal("0.0001")
_TOLERANCE = Decimal("0.05")


def _quantize_money(value: Decimal) -> Decimal:
    return value.quantize(_MONEY, rounding=ROUND_HALF_UP)


def _https_url(value: str) -> str:
    parsed = urlparse(value.strip())
    if parsed.scheme != "https" or not parsed.hostname:
        raise ValueError("public pricing source URLs must use HTTPS")
    return value.strip()


class LoanTermObservationInput(BaseModel):
    app_id: str = Field(min_length=1, max_length=36)
    institution_id: str | None = Field(default=None, max_length=36)
    source_type: Literal[
        "public_disclosure",
        "marketplace_listing",
        "borrower_report",
        "manual_test",
        "regulator_publication",
    ]
    source_provider: str = Field(min_length=1, max_length=120)
    source_url: str | None = Field(default=None, max_length=1000)
    observed_at: object
    currency: str = Field(default="KES", min_length=3, max_length=3)
    amount_received: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    total_repayment: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    term_days: int = Field(ge=1, le=3650)
    advertised_interest_rate_percent: Decimal | None = Field(
        default=None, ge=0, max_digits=10, decimal_places=4
    )
    advertised_rate_basis: Literal[
        "daily", "weekly", "monthly", "term", "annual", "unspecified"
    ] = "unspecified"
    interest_amount: Decimal = Field(default=Decimal("0.00"), ge=0, max_digits=14, decimal_places=2)
    processing_fee: Decimal = Field(default=Decimal("0.00"), ge=0, max_digits=14, decimal_places=2)
    service_fee: Decimal = Field(default=Decimal("0.00"), ge=0, max_digits=14, decimal_places=2)
    insurance_fee: Decimal = Field(default=Decimal("0.00"), ge=0, max_digits=14, decimal_places=2)
    disbursement_fee: Decimal = Field(default=Decimal("0.00"), ge=0, max_digits=14, decimal_places=2)
    other_mandatory_fees: Decimal = Field(
        default=Decimal("0.00"), ge=0, max_digits=14, decimal_places=2
    )
    disclosed_late_fee: Decimal = Field(default=Decimal("0.00"), ge=0, max_digits=14, decimal_places=2)
    disclosed_rollover_fee: Decimal = Field(
        default=Decimal("0.00"), ge=0, max_digits=14, decimal_places=2
    )

    @field_validator("observed_at")
    @classmethod
    def validate_observed_at(cls, value: object) -> object:
        from datetime import datetime

        if not isinstance(value, datetime):
            raise ValueError("observed_at must be a datetime")
        if value.tzinfo is None:
            raise ValueError("observed_at must include a timezone")
        return value

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, value: str) -> str:
        value = value.strip().upper()
        if len(value) != 3 or not value.isalpha():
            raise ValueError("currency must be a three-letter ISO-style code")
        return value

    @field_validator("source_url")
    @classmethod
    def validate_source_url(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        return _https_url(value)

    @field_validator(
        "amount_received",
        "total_repayment",
        "interest_amount",
        "processing_fee",
        "service_fee",
        "insurance_fee",
        "disbursement_fee",
        "other_mandatory_fees",
        "disclosed_late_fee",
        "disclosed_rollover_fee",
    )
    @classmethod
    def normalize_money(cls, value: Decimal) -> Decimal:
        return _quantize_money(value)

    @field_validator("advertised_interest_rate_percent")
    @classmethod
    def normalize_rate(cls, value: Decimal | None) -> Decimal | None:
        if value is None:
            return None
        return value.quantize(_RATE, rounding=ROUND_HALF_UP)

    @model_validator(mode="after")
    def validate_cost_consistency(self) -> LoanTermObservationInput:
        if self.total_repayment < self.amount_received:
            raise ValueError("total_repayment cannot be below amount_received")
        effective_cost = self.total_repayment - self.amount_received
        known_cost = self.interest_amount + sum(
            (
                self.processing_fee,
                self.service_fee,
                self.insurance_fee,
                self.disbursement_fee,
                self.other_mandatory_fees,
            ),
            Decimal("0.00"),
        )
        if known_cost > effective_cost + _TOLERANCE:
            raise ValueError("known interest and mandatory fees exceed total repayment cost")
        return self
