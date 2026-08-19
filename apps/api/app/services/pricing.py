from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Iterable

_MONEY = Decimal("0.01")
_PERCENT = Decimal("0.0001")


def _money(value: Decimal) -> Decimal:
    return value.quantize(_MONEY, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class LoanCostBreakdown:
    effective_cost_amount: Decimal
    effective_cost_percent: Decimal
    known_cost_amount: Decimal
    unexplained_cost_amount: Decimal


def calculate_loan_cost(
    *,
    amount_received: Decimal,
    total_repayment: Decimal,
    interest_amount: Decimal,
    mandatory_fees: Iterable[Decimal],
) -> LoanCostBreakdown:
    amount_received = _money(amount_received)
    total_repayment = _money(total_repayment)
    interest_amount = _money(interest_amount)
    if amount_received <= 0:
        raise ValueError("amount_received must be positive")
    if total_repayment < amount_received:
        raise ValueError("total_repayment cannot be below amount_received")

    effective_cost = _money(total_repayment - amount_received)
    known_cost = _money(interest_amount + sum((_money(value) for value in mandatory_fees), Decimal("0.00")))
    if known_cost > effective_cost + Decimal("0.05"):
        raise ValueError("known cost line items exceed effective cost")
    unexplained_cost = _money(max(effective_cost - known_cost, Decimal("0.00")))
    effective_percent = ((effective_cost / amount_received) * Decimal("100")).quantize(
        _PERCENT, rounding=ROUND_HALF_UP
    )
    return LoanCostBreakdown(
        effective_cost_amount=effective_cost,
        effective_cost_percent=effective_percent,
        known_cost_amount=known_cost,
        unexplained_cost_amount=unexplained_cost,
    )
