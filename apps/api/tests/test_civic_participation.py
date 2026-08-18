from pathlib import Path

import pytest
from pydantic import ValidationError

from app.schemas.civic import CivicDraftRequest
from app.services.civic_participation import (
    ConsultationRegistry,
    build_mailto_link,
    draft_memorandum,
)


def _registry() -> ConsultationRegistry:
    root = Path(__file__).resolve().parents[3]
    return ConsultationRegistry.load(root / "docs" / "public-participation" / "index.json")


def test_registry_uses_only_official_sources_and_explicit_submission_channels() -> None:
    items = _registry().consultations
    assert items
    assert all(item.source_url.startswith("https://") for item in items)
    assert all(item.official_source for item in items)
    assert all(item.channels for item in items)
    assert any("ai" in item.topics for item in items)
    assert any("data privacy" in item.topics for item in items)


def test_draft_is_single_consultation_user_reviewed_and_never_claims_to_be_sent() -> None:
    consultation = _registry().consultations[0]
    request = CivicDraftRequest(
        consultation_id=consultation.id,
        submitter_name="Example Citizen",
        position="support_with_changes",
        points=["Require security testing", "Preserve data-subject rights"],
    )
    draft = draft_memorandum(consultation, request)
    assert consultation.title in draft.subject
    assert "Example Citizen" in draft.body
    assert "Require security testing" in draft.body
    assert draft.sent is False
    assert draft.requires_user_review is True


def test_mailto_link_is_bounded_to_published_consultation_recipients() -> None:
    consultation = _registry().consultations[0]
    email_channel = next(channel for channel in consultation.channels if channel.kind == "email")
    request = CivicDraftRequest(
        consultation_id=consultation.id,
        submitter_name="Example Citizen",
        position="comment",
        points=["Please consider privacy-by-design safeguards."],
    )
    draft = draft_memorandum(consultation, request)
    link = build_mailto_link(email_channel, draft)
    assert link.startswith("mailto:")
    assert "subject=" in link and "body=" in link
    assert len(email_channel.recipients) <= 3


def test_civic_draft_rejects_empty_points() -> None:
    with pytest.raises(ValidationError):
        CivicDraftRequest(
            consultation_id="x",
            submitter_name="Citizen",
            position="comment",
            points=[],
        )
