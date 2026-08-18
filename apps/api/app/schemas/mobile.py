from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class EvidenceKind(StrEnum):
    sms_sender = "sms_sender"
    call_number = "call_number"
    app_package = "app_package"


class ContributionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: EvidenceKind
    institution_hint: str | None = Field(default=None, max_length=300)
    sender_identifier: str | None = Field(default=None, max_length=120)
    app_package: str | None = Field(default=None, max_length=255)
    observed_at: datetime | None = None
    share_consent: bool = False


class SharedContribution(BaseModel):
    kind: EvidenceKind
    institution_hint: str | None = None
    sender_identifier: str | None = None
    app_package: str | None = None
    observed_at: datetime | None = None
    evidence_fingerprint: str
