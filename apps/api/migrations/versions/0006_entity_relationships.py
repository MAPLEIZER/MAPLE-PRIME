"""typed entity relationships and evidence graph

Revision ID: 0006_entity_relationships
Revises: 0005_loan_pricing
"""

from alembic import op
import sqlalchemy as sa

revision = "0006_entity_relationships"
down_revision = "0005_loan_pricing"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "entity_relationships",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("subject_type", sa.String(length=40), nullable=False),
        sa.Column("subject_id", sa.String(length=160), nullable=False),
        sa.Column("relationship_type", sa.String(length=60), nullable=False),
        sa.Column("object_type", sa.String(length=40), nullable=False),
        sa.Column("object_id", sa.String(length=160), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("review_state", sa.String(length=40), nullable=False),
        sa.Column("methodology_version", sa.String(length=40), nullable=False),
        sa.Column("reviewed_by", sa.String(length=120), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "subject_type",
            "subject_id",
            "relationship_type",
            "object_type",
            "object_id",
            name="uq_entity_relationship_edge",
        ),
    )
    for column in ("subject_type", "subject_id", "relationship_type", "object_type", "object_id", "review_state", "first_seen_at", "last_seen_at", "created_at"):
        op.create_index(f"ix_entity_relationships_{column}", "entity_relationships", [column])

    op.create_table(
        "relationship_evidence",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("relationship_id", sa.String(length=36), nullable=False),
        sa.Column("evidence_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("source_type", sa.String(length=60), nullable=False),
        sa.Column("source_url", sa.String(length=1000), nullable=True),
        sa.Column("source_snapshot_id", sa.String(length=36), nullable=True),
        sa.Column("source_observation_id", sa.String(length=36), nullable=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("evidence_strength", sa.String(length=40), nullable=False),
        sa.Column("evidence_text", sa.Text(), nullable=True),
        sa.Column("structured_claim_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["relationship_id"], ["entity_relationships.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_snapshot_id"], ["source_snapshots.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_observation_id"], ["source_observations.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("evidence_fingerprint", name="uq_relationship_evidence_fingerprint"),
    )
    for column in ("relationship_id", "evidence_fingerprint", "source_type", "source_snapshot_id", "source_observation_id", "observed_at", "evidence_strength", "created_at"):
        op.create_index(f"ix_relationship_evidence_{column}", "relationship_evidence", [column])


def downgrade() -> None:
    op.drop_table("relationship_evidence")
    op.drop_table("entity_relationships")
