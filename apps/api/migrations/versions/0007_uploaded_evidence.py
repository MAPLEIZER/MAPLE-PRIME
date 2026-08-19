"""uploaded evidence documents

Revision ID: 0007_uploaded_evidence
Revises: 0006_entity_relationships
"""

import sqlalchemy as sa
from alembic import op

revision = "0007_uploaded_evidence"
down_revision = "0006_entity_relationships"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "uploaded_evidence_documents",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("document_type", sa.String(length=80), nullable=False),
        sa.Column("source_authority", sa.String(length=80), nullable=False),
        sa.Column("media_type", sa.String(length=120), nullable=False),
        sa.Column("storage_path", sa.String(length=1000), nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=False),
        sa.Column("company_name", sa.String(length=300), nullable=True),
        sa.Column("registration_number", sa.String(length=160), nullable=True),
        sa.Column("application_number", sa.String(length=160), nullable=True),
        sa.Column("extracted_claims_json", sa.Text(), nullable=False),
        sa.Column("verification_state", sa.String(length=60), nullable=False),
        sa.Column("verified_by", sa.String(length=120), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sha256", name="uq_uploaded_evidence_sha256"),
    )
    for column in (
        "sha256",
        "document_type",
        "source_authority",
        "company_name",
        "registration_number",
        "application_number",
        "verification_state",
        "created_at",
    ):
        op.create_index(
            f"ix_uploaded_evidence_documents_{column}",
            "uploaded_evidence_documents",
            [column],
        )


def downgrade() -> None:
    op.drop_table("uploaded_evidence_documents")
