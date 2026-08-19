from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal

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


LoanMessageLabel = Literal[
    "non_loan",
    "loan_marketing",
    "loan_application",
    "loan_approval",
    "loan_disbursement",
    "loan_repayment_reminder",
    "loan_overdue_collection",
    "crb_notice",
    "loan_other",
]


class MessageFeatures(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["kdr-msg-v1"]
    char_length: int = Field(ge=0, le=20_000)
    digit_ratio: float = Field(ge=0.0, le=1.0)
    uppercase_ratio: float = Field(ge=0.0, le=1.0)
    loan_term_hits: int = Field(ge=0, le=100)
    marketing_hits: int = Field(ge=0, le=100)
    approval_hits: int = Field(ge=0, le=100)
    disbursement_hits: int = Field(ge=0, le=100)
    repayment_hits: int = Field(ge=0, le=100)
    overdue_hits: int = Field(ge=0, le=100)
    collection_hits: int = Field(ge=0, le=100)
    crb_hits: int = Field(ge=0, le=100)
    amount_hits: int = Field(ge=0, le=100)
    url_hits: int = Field(ge=0, le=100)
    phone_hits: int = Field(ge=0, le=100)
    sender_is_shortcode: bool
    sender_is_alpha: bool
    hashed_buckets: list[int] = Field(min_length=64, max_length=64)


class MobileTelemetryEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: str = Field(min_length=6, max_length=80)
    client_id: str = Field(min_length=16, max_length=80)
    source_kind: Literal["shared_text", "sms_scan", "manual"]
    app_version: str = Field(min_length=1, max_length=80)
    model_version: str = Field(min_length=1, max_length=80)
    predicted_label: LoanMessageLabel
    confidence: float = Field(ge=0.0, le=1.0)
    user_label: LoanMessageLabel | None = None
    features: MessageFeatures


class MobileTelemetryBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    events: list[MobileTelemetryEvent] = Field(min_length=1, max_length=250)


class MobileLabelUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    label: LoanMessageLabel
