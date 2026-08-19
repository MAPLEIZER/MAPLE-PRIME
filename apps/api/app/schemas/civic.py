from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

_EMAIL_RE = re.compile(r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")


class CivicChannel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["email", "form"]
    label: str = Field(min_length=1, max_length=160)
    url: str | None = Field(default=None, max_length=1000)
    recipients: list[str] = Field(default_factory=list, max_length=3)

    @model_validator(mode="after")
    def validate_channel(self) -> CivicChannel:
        if self.kind == "email":
            if not self.recipients or any(not _EMAIL_RE.fullmatch(value) for value in self.recipients):
                raise ValueError("email channel requires valid published recipients")
        if self.kind == "form" and (not self.url or not self.url.startswith("https://")):
            raise ValueError("form channel requires HTTPS URL")
        return self


class Consultation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1, max_length=120)
    title: str = Field(min_length=1, max_length=400)
    agency: str = Field(min_length=1, max_length=240)
    status: Literal["open", "closed", "upcoming"]
    deadline: str
    topics: list[str] = Field(min_length=1, max_length=20)
    source_url: str
    official_source: bool
    channels: list[CivicChannel] = Field(min_length=1, max_length=5)


class CivicDraftRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    consultation_id: str = Field(min_length=1, max_length=120)
    submitter_name: str = Field(min_length=2, max_length=120)
    position: Literal["support", "oppose", "support_with_changes", "comment"]
    points: list[str] = Field(min_length=1, max_length=12)

    @model_validator(mode="after")
    def validate_points(self) -> CivicDraftRequest:
        cleaned = [point.strip() for point in self.points]
        if any(not point or len(point) > 500 for point in cleaned):
            raise ValueError("each participation point must be 1-500 characters")
        self.points = cleaned
        return self


class CivicDraft(BaseModel):
    subject: str
    body: str
    sent: bool = False
    requires_user_review: bool = True
