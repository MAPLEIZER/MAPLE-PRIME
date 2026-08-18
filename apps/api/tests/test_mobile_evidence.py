from app.schemas.mobile import ContributionCreate, EvidenceKind
from app.services.mobile_evidence import sanitize_contribution


def test_mobile_contribution_never_accepts_raw_message_body() -> None:
    item = ContributionCreate(kind=EvidenceKind.sms_sender, institution_hint="Example Credit", sender_identifier="EXAMPLE", app_package="com.example.credit", observed_at="2026-08-18T06:00:00Z", raw_message_body="Your loan is due tomorrow")
    sanitized = sanitize_contribution(item)
    assert not hasattr(sanitized, "raw_message_body")
    assert sanitized.sender_identifier == "EXAMPLE"


def test_mobile_contribution_requires_explicit_share_consent() -> None:
    item = ContributionCreate(kind=EvidenceKind.app_package, institution_hint="Example Credit", app_package="com.example.credit", share_consent=False)
    try:
        sanitize_contribution(item)
    except ValueError as exc:
        assert "consent" in str(exc).lower()
    else:
        raise AssertionError("contribution without explicit share consent must be rejected")
