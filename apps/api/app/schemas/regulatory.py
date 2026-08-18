from datetime import date, datetime
from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class EvidenceLevel(StrEnum):
    VERIFIED = "verified"
    REVIEW = "review"
    UNKNOWN = "unknown"


class RegulatedEntity(BaseModel):
    id: UUID
    canonical_name: str
    trading_names: list[str] = []
    categories: list[str] = []
    website: str | None = None


class RegulatorObservation(BaseModel):
    regulator: str
    status: str
    external_id: str | None = None
    source_url: str
    source_published_at: date | None = None
    observed_at: datetime
    evidence_level: EvidenceLevel = EvidenceLevel.VERIFIED


class ReconciliationFinding(BaseModel):
    code: str
    severity: str
    entity_id: UUID | None = None
    title: str
    detail: str
    source_snapshot_ids: list[UUID] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    requires_manual_review: bool = False


class ReconciliationReviewInput(BaseModel):
    decision: Literal["confirmed", "rejected"]
    institution_id: str | None = None
