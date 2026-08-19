from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models import new_id


class EntityRelationship(Base):
    __tablename__ = "entity_relationships"
    __table_args__ = (
        UniqueConstraint(
            "subject_type",
            "subject_id",
            "relationship_type",
            "object_type",
            "object_id",
            name="uq_entity_relationship_edge",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    subject_type: Mapped[str] = mapped_column(String(40), index=True)
    subject_id: Mapped[str] = mapped_column(String(160), index=True)
    relationship_type: Mapped[str] = mapped_column(String(60), index=True)
    object_type: Mapped[str] = mapped_column(String(40), index=True)
    object_id: Mapped[str] = mapped_column(String(160), index=True)
    confidence: Mapped[float] = mapped_column(Float)
    review_state: Mapped[str] = mapped_column(String(40), default="candidate", index=True)
    methodology_version: Mapped[str] = mapped_column(String(40), default="relationship-v1")
    reviewed_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), index=True
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), index=True
    )


class RelationshipEvidence(Base):
    __tablename__ = "relationship_evidence"
    __table_args__ = (
        UniqueConstraint("evidence_fingerprint", name="uq_relationship_evidence_fingerprint"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    relationship_id: Mapped[str] = mapped_column(
        ForeignKey("entity_relationships.id", ondelete="CASCADE"), index=True
    )
    evidence_fingerprint: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    source_type: Mapped[str] = mapped_column(String(60), index=True)
    source_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    source_snapshot_id: Mapped[str | None] = mapped_column(
        ForeignKey("source_snapshots.id", ondelete="SET NULL"), nullable=True, index=True
    )
    source_observation_id: Mapped[str | None] = mapped_column(
        ForeignKey("source_observations.id", ondelete="SET NULL"), nullable=True, index=True
    )
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    evidence_strength: Mapped[str] = mapped_column(String(40), index=True)
    evidence_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    structured_claim_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), index=True
    )
