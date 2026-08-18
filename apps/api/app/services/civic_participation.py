from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlencode

from app.schemas.civic import CivicChannel, CivicDraft, CivicDraftRequest, Consultation


@dataclass(frozen=True)
class ConsultationRegistry:
    consultations: list[Consultation]

    @classmethod
    def load(cls, path: Path) -> ConsultationRegistry:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            raise ValueError("consultation registry must be a list")
        consultations = [Consultation.model_validate(item) for item in payload]
        if any(not item.official_source or not item.source_url.startswith("https://") for item in consultations):
            raise ValueError("consultations must use official HTTPS sources")
        return cls(consultations=consultations)

    def get(self, consultation_id: str) -> Consultation:
        for item in self.consultations:
            if item.id == consultation_id:
                return item
        raise KeyError(consultation_id)


def draft_memorandum(consultation: Consultation, request: CivicDraftRequest) -> CivicDraft:
    position_labels = {
        "support": "I support the proposal.",
        "oppose": "I oppose the proposal.",
        "support_with_changes": "I support the policy objective subject to the changes below.",
        "comment": "I submit the following comments for consideration.",
    }
    bullets = "\n".join(f"{index}. {point}" for index, point in enumerate(request.points, 1))
    body = (
        "To the relevant public participation committee/secretariat,\n\n"
        f"RE: {consultation.title}\n\n"
        f"My name is {request.submitter_name}. {position_labels[request.position]}\n\n"
        f"My comments are:\n{bullets}\n\n"
        "I request that these views be considered as part of the public participation record. "
        "I have reviewed this memorandum before submission.\n\n"
        f"Source notice: {consultation.source_url}\n"
        f"Submitted by: {request.submitter_name}\n"
    )
    return CivicDraft(
        subject=f"Public participation memorandum — {consultation.title}"[:250],
        body=body[:12_000],
        sent=False,
        requires_user_review=True,
    )


def build_mailto_link(channel: CivicChannel, draft: CivicDraft) -> str:
    if channel.kind != "email" or not channel.recipients:
        raise ValueError("consultation channel is not an email channel")
    if len(channel.recipients) > 3:
        raise ValueError("bulk participation recipients are not allowed")
    recipients = ",".join(channel.recipients)
    return f"mailto:{recipients}?{urlencode({'subject': draft.subject, 'body': draft.body})}"
