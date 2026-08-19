from __future__ import annotations

from dataclasses import dataclass

from app.schemas.mobile import LoanMessageLabel, MessageFeatures

MODEL_VERSION = "rules-v1"


@dataclass(frozen=True)
class ClassificationResult:
    label: LoanMessageLabel
    confidence: float
    model_version: str = MODEL_VERSION


def _confidence(base: float, signal: int) -> float:
    return round(min(0.98, base + min(signal, 8) * 0.04), 4)


def classify_features(features: MessageFeatures) -> ClassificationResult:
    loan_signal = features.loan_term_hits + features.amount_hits

    if features.collection_hits > 0 or (features.overdue_hits >= 2 and loan_signal > 0):
        return ClassificationResult(
            "loan_overdue_collection",
            _confidence(0.62, features.collection_hits + features.overdue_hits + loan_signal),
        )
    if features.crb_hits > 0 and (loan_signal > 0 or features.overdue_hits > 0):
        return ClassificationResult("crb_notice", _confidence(0.62, features.crb_hits + loan_signal))
    if features.repayment_hits > 0 and loan_signal > 0:
        return ClassificationResult(
            "loan_repayment_reminder",
            _confidence(0.58, features.repayment_hits + loan_signal),
        )
    if features.disbursement_hits > 0 and loan_signal > 0:
        return ClassificationResult(
            "loan_disbursement",
            _confidence(0.58, features.disbursement_hits + loan_signal),
        )
    if features.approval_hits > 0 and loan_signal > 0:
        return ClassificationResult(
            "loan_approval",
            _confidence(0.56, features.approval_hits + loan_signal),
        )
    if features.marketing_hits > 0 and features.loan_term_hits > 0:
        return ClassificationResult(
            "loan_marketing",
            _confidence(0.54, features.marketing_hits + features.loan_term_hits),
        )
    if features.loan_term_hits >= 2:
        return ClassificationResult("loan_other", _confidence(0.50, features.loan_term_hits))
    return ClassificationResult("non_loan", 0.72)
