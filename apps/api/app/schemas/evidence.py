from typing import Literal

from pydantic import BaseModel


class EvidenceDocumentReviewInput(BaseModel):
    decision: Literal["manual_verified", "rejected"]
