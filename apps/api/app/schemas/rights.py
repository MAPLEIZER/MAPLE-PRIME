from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field


class RightType(StrEnum):
    ACCESS = "access"
    RECTIFICATION = "rectification"
    ERASURE = "erasure"
    RESTRICTION = "restriction"
    OBJECTION = "objection"
    MARKETING_SUPPRESSION = "marketing_suppression"
    CONSENT_WITHDRAWAL = "consent_withdrawal"
    CRB_DISPUTE = "crb_dispute"


class RequestState(StrEnum):
    DRAFT = "draft"
    AWAITING_APPROVAL = "awaiting_approval"
    READY = "ready"
    SENT = "sent"
    AWAITING_RESPONSE = "awaiting_response"
    MANUAL_REQUIRED = "manual_required"
    RESPONSE_RECEIVED = "response_received"
    SATISFIED_PENDING_VERIFICATION = "satisfied_pending_verification"
    CLOSED = "closed"
    ESCALATION_REVIEW = "escalation_review"


class RightsRequestCreate(BaseModel):
    entity_id: UUID
    right_type: RightType
    relationship_basis: str = Field(min_length=1, max_length=500)
    user_notes: str | None = Field(default=None, max_length=4000)


class RightsRequestPreview(BaseModel):
    subject: str
    body: str
    warnings: list[str] = []
    requires_user_approval: bool = True
