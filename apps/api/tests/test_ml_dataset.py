from datetime import UTC, datetime

from app.db.models import MobileTelemetryEventRecord
from app.ml.dataset import FEATURE_NAMES, build_training_rows, feature_vector
from app.schemas.mobile import MessageFeatures


def _features() -> MessageFeatures:
    return MessageFeatures(
        schema_version="kdr-msg-v1",
        char_length=100,
        digit_ratio=0.1,
        uppercase_ratio=0.02,
        loan_term_hits=2,
        marketing_hits=0,
        approval_hits=0,
        disbursement_hits=0,
        repayment_hits=3,
        overdue_hits=0,
        collection_hits=0,
        crb_hits=0,
        amount_hits=1,
        url_hits=0,
        phone_hits=0,
        sender_is_shortcode=True,
        sender_is_alpha=False,
        hashed_buckets=[0] * 64,
    )


def test_feature_vector_is_stable_numeric_80_dimension_schema() -> None:
    vector = feature_vector(_features())
    assert len(vector) == 80
    assert len(FEATURE_NAMES) == 80
    assert all(isinstance(value, float) for value in vector)


def test_training_rows_require_explicit_user_labels() -> None:
    feature_json = _features().model_dump_json()
    labeled = MobileTelemetryEventRecord(
        id="labeled",
        client_hash="a" * 64,
        source_kind="sms_scan",
        app_version="alpha",
        model_version="rules-v1",
        predicted_label="loan_repayment_reminder",
        server_label="loan_repayment_reminder",
        confidence=0.9,
        user_label="loan_repayment_reminder",
        features_json=feature_json,
        created_at=datetime.now(UTC),
    )
    unlabeled = MobileTelemetryEventRecord(
        id="unlabeled",
        client_hash="b" * 64,
        source_kind="sms_scan",
        app_version="alpha",
        model_version="rules-v1",
        predicted_label="loan_repayment_reminder",
        server_label="loan_repayment_reminder",
        confidence=0.9,
        user_label=None,
        features_json=feature_json,
        created_at=datetime.now(UTC),
    )
    rows = build_training_rows([labeled, unlabeled])
    assert len(rows) == 1
    assert rows[0].label == "loan_repayment_reminder"
    assert rows[0].event_id == "labeled"
