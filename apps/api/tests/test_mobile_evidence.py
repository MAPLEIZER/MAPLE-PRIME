import pytest
from pydantic import ValidationError

from app.schemas.mobile import ContributionCreate, EvidenceKind
from app.services.mobile_evidence import prepare_shared_contribution


def test_backend_contract_rejects_raw_message_content() -> None:
    with pytest.raises(ValidationError):
        ContributionCreate.model_validate(
            {
                "kind": "sms_sender",
                "institution_hint": "Example Credit",
                "sender_identifier": "EXAMPLE",
                "raw_message_body": "Your loan is due tomorrow",
                "share_consent": True,
            }
        )


def test_mobile_contribution_requires_explicit_share_consent() -> None:
    item = ContributionCreate(
        kind=EvidenceKind.app_package,
        institution_hint="Example Credit",
        app_package="com.example.credit",
        share_consent=False,
    )
    with pytest.raises(ValueError, match="consent"):
        prepare_shared_contribution(item)


def test_shared_record_contains_only_mapping_evidence() -> None:
    item = ContributionCreate(
        kind=EvidenceKind.sms_sender,
        institution_hint="Example Credit",
        sender_identifier="EXAMPLE",
        app_package="com.example.credit",
        observed_at="2026-08-18T06:00:00Z",
        share_consent=True,
    )
    shared = prepare_shared_contribution(item)
    assert shared.sender_identifier == "EXAMPLE"
    assert set(shared.model_dump()) <= {
        "kind",
        "institution_hint",
        "sender_identifier",
        "app_package",
        "observed_at",
        "evidence_fingerprint",
    }
