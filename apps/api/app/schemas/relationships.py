from __future__ import annotations

from datetime import datetime
from typing import Literal
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator

EntityType = Literal["marketplace_app", "institution", "external_entity"]
RelationshipType = Literal[
    "published_by",
    "developed_by",
    "operated_by",
    "lends_on_behalf_of",
    "trading_name_of",
    "licensed_as",
    "data_controller_is",
    "subsidiary_of",
    "parent_company_is",
    "beneficially_owned_by",
]
EvidenceStrength = Literal["weak", "moderate", "strong", "very_strong"]


class RelationshipInput(BaseModel):
    subject_type: EntityType
    subject_id: str = Field(min_length=1, max_length=160)
    relationship_type: RelationshipType
    object_type: EntityType
    object_id: str = Field(min_length=1, max_length=160)
    confidence: float = Field(ge=0.0, le=0.98)
    observed_at: datetime | None = None
    methodology_version: str = Field(default="relationship-v1", min_length=1, max_length=40)


class RelationshipEvidenceInput(BaseModel):
    source_type: str = Field(min_length=1, max_length=60)
    source_url: str | None = Field(default=None, max_length=1000)
    source_snapshot_id: str | None = Field(default=None, max_length=36)
    source_observation_id: str | None = Field(default=None, max_length=36)
    observed_at: datetime
    evidence_strength: EvidenceStrength
    evidence_text: str | None = Field(default=None, max_length=5000)
    structured_claim: dict[str, object] = Field(default_factory=dict)

    @field_validator("source_url")
    @classmethod
    def validate_source_url(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        parsed = urlparse(value.strip())
        if parsed.scheme != "https" or not parsed.hostname:
            raise ValueError("public evidence URLs must use HTTPS")
        return value.strip()

    @field_validator("observed_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("observed_at must include a timezone")
        return value


class RelationshipReviewInput(BaseModel):
    decision: Literal["confirmed", "rejected"]
