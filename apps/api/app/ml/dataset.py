from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from app.db.models import MobileTelemetryEventRecord
from app.schemas.mobile import MessageFeatures

_BASE_FEATURE_NAMES = [
    "char_length",
    "digit_ratio",
    "uppercase_ratio",
    "loan_term_hits",
    "marketing_hits",
    "approval_hits",
    "disbursement_hits",
    "repayment_hits",
    "overdue_hits",
    "collection_hits",
    "crb_hits",
    "amount_hits",
    "url_hits",
    "phone_hits",
    "sender_is_shortcode",
    "sender_is_alpha",
]
FEATURE_NAMES = tuple(_BASE_FEATURE_NAMES + [f"hashed_bucket_{index:02d}" for index in range(64)])


@dataclass(frozen=True)
class TrainingRow:
    event_id: str
    label: str
    features: tuple[float, ...]


def feature_vector(features: MessageFeatures) -> tuple[float, ...]:
    base = [
        float(features.char_length),
        float(features.digit_ratio),
        float(features.uppercase_ratio),
        float(features.loan_term_hits),
        float(features.marketing_hits),
        float(features.approval_hits),
        float(features.disbursement_hits),
        float(features.repayment_hits),
        float(features.overdue_hits),
        float(features.collection_hits),
        float(features.crb_hits),
        float(features.amount_hits),
        float(features.url_hits),
        float(features.phone_hits),
        1.0 if features.sender_is_shortcode else 0.0,
        1.0 if features.sender_is_alpha else 0.0,
    ]
    vector = tuple(base + [float(value) for value in features.hashed_buckets])
    if len(vector) != len(FEATURE_NAMES):
        raise ValueError("message feature schema drift detected")
    return vector


def build_training_rows(records: Iterable[MobileTelemetryEventRecord]) -> list[TrainingRow]:
    rows: list[TrainingRow] = []
    for record in records:
        if not record.user_label:
            continue
        features = MessageFeatures.model_validate_json(record.features_json)
        rows.append(TrainingRow(event_id=record.id, label=record.user_label, features=feature_vector(features)))
    return rows
