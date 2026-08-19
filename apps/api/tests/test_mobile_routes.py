from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings
from app.db.base import Base
from app.db.session import get_session
from app.main import app
from app.schemas.mobile import MessageFeatures, MobileTelemetryEvent


def _payload() -> dict[str, object]:
    features = MessageFeatures(
        schema_version="kdr-msg-v1",
        char_length=88,
        digit_ratio=0.12,
        uppercase_ratio=0.03,
        loan_term_hits=1,
        marketing_hits=0,
        approval_hits=0,
        disbursement_hits=0,
        repayment_hits=2,
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
    return MobileTelemetryEvent(
        event_id="evt-route-1",
        client_id="984e77a9-4d96-4443-81d4-3da319fa6582",
        source_kind="sms_scan",
        app_version="0.1.0-alpha.1-direct",
        model_version="rules-v1",
        predicted_label="loan_repayment_reminder",
        confidence=0.81,
        features=features,
    ).model_dump()


def test_mobile_telemetry_route_is_disabled_by_default(monkeypatch) -> None:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)

    def override_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    monkeypatch.setenv("KDR_MOBILE_TELEMETRY_ENABLED", "false")
    monkeypatch.setenv("KDR_MOBILE_API_TOKEN", "test-token")
    get_settings.cache_clear()
    try:
        response = TestClient(app).post(
            "/api/v1/mobile/telemetry",
            json=_payload(),
            headers={"Authorization": "Bearer test-token"},
        )
        assert response.status_code == 503
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()


def test_mobile_telemetry_route_accepts_derived_features_with_valid_token(monkeypatch) -> None:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)

    def override_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    monkeypatch.setenv("KDR_MOBILE_TELEMETRY_ENABLED", "true")
    monkeypatch.setenv("KDR_MOBILE_API_TOKEN", "test-token")
    get_settings.cache_clear()
    try:
        response = TestClient(app).post(
            "/api/v1/mobile/telemetry",
            json=_payload(),
            headers={"Authorization": "Bearer test-token"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["accepted"] is True
        assert data["server_classification"]["label"] == "loan_repayment_reminder"
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()
