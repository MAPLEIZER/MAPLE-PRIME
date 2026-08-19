"""persist reconciliation findings

Revision ID: 0002_reconciliation_findings
Revises: 0001_alpha_core
"""

import sqlalchemy as sa
from alembic import op

revision = "0002_reconciliation_findings"
down_revision = "0001_alpha_core"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "reconciliation_findings",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("finding_key", sa.String(64), nullable=False),
        sa.Column("left_source_key", sa.String(255), nullable=False),
        sa.Column("right_source_key", sa.String(255), nullable=True),
        sa.Column("finding_type", sa.String(50), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("review_state", sa.String(40), nullable=False),
        sa.Column("reviewed_by", sa.String(120), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "resolved_institution_id",
            sa.String(36),
            sa.ForeignKey("institutions.id"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("finding_key", name="uq_reconciliation_finding_key"),
    )
    op.create_index("ix_reconciliation_findings_finding_key", "reconciliation_findings", ["finding_key"])
    op.create_index("ix_reconciliation_findings_left_source_key", "reconciliation_findings", ["left_source_key"])
    op.create_index("ix_reconciliation_findings_right_source_key", "reconciliation_findings", ["right_source_key"])
    op.create_index("ix_reconciliation_findings_finding_type", "reconciliation_findings", ["finding_type"])
    op.create_index("ix_reconciliation_findings_review_state", "reconciliation_findings", ["review_state"])
    op.create_index("ix_reconciliation_findings_resolved_institution_id", "reconciliation_findings", ["resolved_institution_id"])
    op.create_index("ix_reconciliation_findings_created_at", "reconciliation_findings", ["created_at"])


def downgrade() -> None:
    op.drop_table("reconciliation_findings")
