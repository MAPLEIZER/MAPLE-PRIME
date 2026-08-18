import hashlib

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.mobile_auth import validate_mobile_bearer
from app.db.base import Base
from app.db.models import MobileTelemetryEventRecord
from app.db.repositories import MobileTelemetryRepository
from app.schemas.mobile import MessageFeatures, MobileTelemetryEvent


def _event() -> MobileTelemetryEvent:
    return MobileTelemetryEvent(
        event_id="evt-123",
        client_id="9f12e39e-2e2b-454e-9d12-dca90b5b94c8",
        source_kind="sms_scan",
        app_version="0.1.0-alpha.1-direct",
        model_version="rules-v1",
        predicted_label="loan_repayment_reminder",
        confidence=0.88,
        user_label=None,
        features=MessageFeatures(
            schema_version="kdr-msg-v1",
            char_length=98,
            digit_ratio=0.14,
            uppercase_ratio=0.04,
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
        ),
    )


def test_mobile_bearer_requires_enabled_server_and_constant_value() -> None:
    with pytest.raises(HTTPException) as disabled:
        validate_mobile_bearer("Bearer secret", enabled=False, configured_token="secret")
    assert disabled.value.status_code == 503

    with pytest.raises(HTTPException) as wrong:
        validate_mobile_bearer("Bearer wrong", enabled=True, configured_token="secret")
    assert wrong.value.status_code == 403

    assert validate_mobile_bearer("Bearer secret", enabled=True, configured_token="secret") == "secret"


def test_telemetry_repository_hashes_client_id_and_persists_only_features() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        stored = MobileTelemetryRepository(session).add(_event())
        session.commit()
        row = session.scalar(select(MobileTelemetryEventRecord).where(MobileTelemetryEventRecord.id == stored.id))
        assert row is not None
        assert row.client_hash == hashlib.sha256(_event().client_id.encode()).hexdigest()
        assert _event().client_id not in row.features_json
        assert "Your loan" not in row.features_json
