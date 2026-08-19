"""alpha core schema

Revision ID: 0001_alpha_core
Revises:
"""

import sqlalchemy as sa
from alembic import op

revision = "0001_alpha_core"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "institutions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("legal_name", sa.String(300), nullable=False),
        sa.Column("trading_name", sa.String(300), nullable=True),
        sa.Column("category", sa.String(80), nullable=False),
        sa.Column("website", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "institution_aliases",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "institution_id",
            sa.String(36),
            sa.ForeignKey("institutions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("alias", sa.String(300), nullable=False),
        sa.Column("alias_type", sa.String(40), nullable=False),
        sa.UniqueConstraint("institution_id", "alias", name="uq_institution_alias"),
    )
    op.create_table(
        "source_snapshots",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("source_id", sa.String(120), nullable=False),
        sa.Column("source_url", sa.String(1000), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("media_type", sa.String(120), nullable=False),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("storage_path", sa.String(1000), nullable=False),
    )
    op.create_table(
        "source_observations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "snapshot_id",
            sa.String(36),
            sa.ForeignKey("source_snapshots.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "institution_id",
            sa.String(36),
            sa.ForeignKey("institutions.id"),
            nullable=True,
        ),
        sa.Column("regulator", sa.String(80), nullable=False),
        sa.Column("external_id", sa.String(160), nullable=True),
        sa.Column("status", sa.String(80), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
    )
    op.create_table(
        "rights_requests",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "institution_id",
            sa.String(36),
            sa.ForeignKey("institutions.id"),
            nullable=True,
        ),
        sa.Column("right_type", sa.String(80), nullable=False),
        sa.Column("state", sa.String(80), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "audit_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("event_type", sa.String(120), nullable=False),
        sa.Column("actor", sa.String(120), nullable=False),
        sa.Column("subject_id", sa.String(36), nullable=True),
        sa.Column("detail_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "mapping_evidence",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "institution_id",
            sa.String(36),
            sa.ForeignKey("institutions.id"),
            nullable=True,
        ),
        sa.Column("kind", sa.String(50), nullable=False),
        sa.Column("sender_identifier", sa.String(120), nullable=True),
        sa.Column("app_package", sa.String(255), nullable=True),
        sa.Column("evidence_fingerprint", sa.String(64), nullable=False),
        sa.Column("verification_state", sa.String(40), nullable=False),
        sa.Column("contributed", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "evidence_fingerprint",
            name="uq_mapping_evidence_fingerprint",
        ),
    )


def downgrade() -> None:
    op.drop_table("mapping_evidence")
    op.drop_table("audit_events")
    op.drop_table("rights_requests")
    op.drop_table("source_observations")
    op.drop_table("source_snapshots")
    op.drop_table("institution_aliases")
    op.drop_table("institutions")
