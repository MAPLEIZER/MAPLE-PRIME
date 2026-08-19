from __future__ import annotations

import json
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.evidence_models import UploadedEvidenceDocument


class EvidenceDocumentRepository:
    VALID_REVIEW_STATES = frozenset({"manual_verified", "rejected"})

    def __init__(self, session: Session):
        self.session = session

    def get(self, document_id: str) -> UploadedEvidenceDocument | None:
        return self.session.get(UploadedEvidenceDocument, document_id)

    def list(self, *, limit: int = 200) -> list[UploadedEvidenceDocument]:
        statement = (
            select(UploadedEvidenceDocument)
            .order_by(UploadedEvidenceDocument.created_at.desc())
            .limit(max(1, min(limit, 500)))
        )
        return list(self.session.scalars(statement))

    def record(
        self,
        *,
        sha256: str,
        document_type: str,
        storage_path: str,
        page_count: int,
        claims: dict[str, object],
    ) -> UploadedEvidenceDocument:
        existing = self.session.scalar(
            select(UploadedEvidenceDocument).where(UploadedEvidenceDocument.sha256 == sha256)
        )
        if existing is not None:
            return existing
        item = UploadedEvidenceDocument(
            sha256=sha256,
            document_type=document_type,
            storage_path=storage_path,
            page_count=page_count,
            company_name=str(claims.get("company_name") or "") or None,
            registration_number=str(claims.get("registration_number") or "") or None,
            application_number=str(claims.get("application_number") or "") or None,
            extracted_claims_json=json.dumps(claims, sort_keys=True, separators=(",", ":")),
            verification_state="uploaded_unverified",
        )
        self.session.add(item)
        self.session.flush()
        return item

    def review(
        self, document_id: str, *, decision: str, reviewer: str
    ) -> UploadedEvidenceDocument:
        if decision not in self.VALID_REVIEW_STATES:
            raise ValueError("decision must be manual_verified or rejected")
        item = self.get(document_id)
        if item is None:
            raise KeyError(document_id)
        item.verification_state = decision
        item.verified_by = reviewer
        item.verified_at = datetime.now(UTC)
        self.session.flush()
        return item
