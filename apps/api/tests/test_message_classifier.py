import pytest
from pydantic import ValidationError

from app.schemas.mobile import MessageFeatures, MobileTelemetryEvent
from app.services.message_classifier import classify_features


def _features(**overrides: object) -> MessageFeatures:
    values: dict[str, object] = {
        "schema_version": "kdr-msg-v1",
        "char_length": 120,
        "digit_ratio": 0.10,
        "uppercase_ratio": 0.05,
        "loan_term_hits": 0,
        "marketing_hits": 0,
        "approval_hits": 0,
        "disbursement_hits": 0,
        "repayment_hits": 0,
        "overdue_hits": 0,
        "collection_hits": 0,
        "crb_hits": 0,
        "amount_hits": 0,
        "url_hits": 0,
        "phone_hits": 0,
        "sender_is_shortcode": False,
        "sender_is_alpha": True,
        "hashed_buckets": [0] * 64,
    }
    values.update(overrides)
    return MessageFeatures(**values)


def test_rule_baseline_classifies_repayment_and_collection_without_raw_text() -> None:
    repayment = classify_features(
        _features(loan_term_hits=2, repayment_hits=3, amount_hits=2)
    )
    assert repayment.label == "loan_repayment_reminder"
    assert repayment.confidence >= 0.5

    collection = classify_features(
        _features(loan_term_hits=1, overdue_hits=2, collection_hits=3, repayment_hits=1)
    )
    assert collection.label == "loan_overdue_collection"


def test_low_signal_message_is_non_loan() -> None:
    assert classify_features(_features()).label == "non_loan"


def test_feature_schema_is_fixed_and_telemetry_forbids_raw_message_fields() -> None:
    with pytest.raises(ValidationError):
        _features(hashed_buckets=[0] * 63)

    with pytest.raises(ValidationError):
        MobileTelemetryEvent(
            event_id="event-1",
            client_id="4aadc8ef-1160-4f78-9288-f9a3e0cb99e4",
            source_kind="shared_text",
            app_version="0.1.0-alpha.1",
            model_version="rules-v1",
            predicted_label="non_loan",
            confidence=0.7,
            features=_features(),
            raw_text="this field must never be accepted",
        )
