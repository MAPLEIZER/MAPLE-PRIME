from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def new_id() -> str:
    return str(uuid4())


class Institution(Base):
    __tablename__ = "institutions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    legal_name: Mapped[str] = mapped_column(String(300), index=True)
    trading_name: Mapped[str | None] = mapped_column(String(300), nullable=True)
    category: Mapped[str] = mapped_column(String(80), index=True)
    website: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    aliases: Mapped[list[InstitutionAlias]] = relationship(
        back_populates="institution", cascade="all, delete-orphan"
    )


class InstitutionAlias(Base):
    __tablename__ = "institution_aliases"
    __table_args__ = (UniqueConstraint("institution_id", "alias", name="uq_institution_alias"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    institution_id: Mapped[str] = mapped_column(
        ForeignKey("institutions.id", ondelete="CASCADE"), index=True
    )
    alias: Mapped[str] = mapped_column(String(300), index=True)
    alias_type: Mapped[str] = mapped_column(String(40), default="trading_name")
    institution: Mapped[Institution] = relationship(back_populates="aliases")


class SourceSnapshot(Base):
    __tablename__ = "source_snapshots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    source_id: Mapped[str] = mapped_column(String(120), index=True)
    source_url: Mapped[str] = mapped_column(String(1000))
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    media_type: Mapped[str] = mapped_column(String(120))
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    storage_path: Mapped[str] = mapped_column(String(1000))


class SourceObservation(Base):
    __tablename__ = "source_observations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    snapshot_id: Mapped[str] = mapped_column(
        ForeignKey("source_snapshots.id", ondelete="CASCADE"), index=True
    )
    institution_id: Mapped[str | None] = mapped_column(
        ForeignKey("institutions.id"), nullable=True, index=True
    )
    regulator: Mapped[str] = mapped_column(String(80), index=True)
    external_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    status: Mapped[str] = mapped_column(String(80), default="observed")
    payload_json: Mapped[str] = mapped_column(Text)


class RightsRequest(Base):
    __tablename__ = "rights_requests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    institution_id: Mapped[str | None] = mapped_column(
        ForeignKey("institutions.id"), nullable=True, index=True
    )
    right_type: Mapped[str] = mapped_column(String(80), index=True)
    state: Mapped[str] = mapped_column(String(80), default="draft", index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    event_type: Mapped[str] = mapped_column(String(120), index=True)
    actor: Mapped[str] = mapped_column(String(120), default="local_user")
    subject_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    detail_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), index=True
    )


class MappingEvidence(Base):
    __tablename__ = "mapping_evidence"
    __table_args__ = (
        UniqueConstraint("evidence_fingerprint", name="uq_mapping_evidence_fingerprint"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    institution_id: Mapped[str | None] = mapped_column(
        ForeignKey("institutions.id"), nullable=True, index=True
    )
    kind: Mapped[str] = mapped_column(String(50), index=True)
    sender_identifier: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    app_package: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    evidence_fingerprint: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    verification_state: Mapped[str] = mapped_column(String(40), default="unverified", index=True)
    contributed: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class ReconciliationFinding(Base):
    __tablename__ = "reconciliation_findings"
    __table_args__ = (UniqueConstraint("finding_key", name="uq_reconciliation_finding_key"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    finding_key: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    left_source_key: Mapped[str] = mapped_column(String(255), index=True)
    right_source_key: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    finding_type: Mapped[str] = mapped_column(String(50), index=True)
    confidence: Mapped[float] = mapped_column(Float)
    summary: Mapped[str] = mapped_column(Text)
    review_state: Mapped[str] = mapped_column(String(40), default="pending", index=True)
    reviewed_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_institution_id: Mapped[str | None] = mapped_column(
        ForeignKey("institutions.id"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), index=True
    )


class MobileTelemetryEventRecord(Base):
    __tablename__ = "mobile_telemetry_events"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    client_hash: Mapped[str] = mapped_column(String(64), index=True)
    source_kind: Mapped[str] = mapped_column(String(40))
    app_version: Mapped[str] = mapped_column(String(80))
    model_version: Mapped[str] = mapped_column(String(80))
    predicted_label: Mapped[str] = mapped_column(String(80), index=True)
    server_label: Mapped[str] = mapped_column(String(80))
    confidence: Mapped[float] = mapped_column(Float)
    user_label: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    features_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), index=True
    )
