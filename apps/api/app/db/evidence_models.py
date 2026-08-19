from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models import new_id


class UploadedEvidenceDocument(Base):
    __tablename__ = "uploaded_evidence_documents"
    __table_args__ = (UniqueConstraint("sha256", name="uq_uploaded_evidence_sha256"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    sha256: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    document_type: Mapped[str] = mapped_column(String(80), index=True)
    source_authority: Mapped[str] = mapped_column(String(80), default="BRS", index=True)
    media_type: Mapped[str] = mapped_column(String(120), default="application/pdf")
    storage_path: Mapped[str] = mapped_column(String(1000))
    page_count: Mapped[int] = mapped_column(Integer, default=0)
    company_name: Mapped[str | None] = mapped_column(String(300), nullable=True, index=True)
    registration_number: Mapped[str | None] = mapped_column(String(160), nullable=True, index=True)
    application_number: Mapped[str | None] = mapped_column(String(160), nullable=True, index=True)
    extracted_claims_json: Mapped[str] = mapped_column(Text, default="{}")
    verification_state: Mapped[str] = mapped_column(
        String(60), default="uploaded_unverified", index=True
    )
    verified_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), index=True
    )
