"""add append-only loan pricing observations

Revision ID: 0005_loan_pricing
Revises: 0004_app_identity_registry
"""

import sqlalchemy as sa
from alembic import op

revision = "0005_loan_pricing"
down_revision = "0004_app_identity_registry"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "loan_term_observations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("app_id", sa.String(36), sa.ForeignKey("marketplace_apps.id"), nullable=False),
        sa.Column("institution_id", sa.String(36), sa.ForeignKey("institutions.id"), nullable=True),
        sa.Column("observation_hash", sa.String(64), nullable=False),
        sa.Column("source_type", sa.String(40), nullable=False),
        sa.Column("source_provider", sa.String(120), nullable=False),
        sa.Column("source_url", sa.String(1000), nullable=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("amount_received", sa.Numeric(14, 2), nullable=False),
        sa.Column("total_repayment", sa.Numeric(14, 2), nullable=False),
        sa.Column("term_days", sa.Integer(), nullable=False),
        sa.Column("advertised_interest_rate_percent", sa.Numeric(10, 4), nullable=True),
        sa.Column("advertised_rate_basis", sa.String(20), nullable=False),
        sa.Column("interest_amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("processing_fee", sa.Numeric(14, 2), nullable=False),
        sa.Column("service_fee", sa.Numeric(14, 2), nullable=False),
        sa.Column("insurance_fee", sa.Numeric(14, 2), nullable=False),
        sa.Column("disbursement_fee", sa.Numeric(14, 2), nullable=False),
        sa.Column("other_mandatory_fees", sa.Numeric(14, 2), nullable=False),
        sa.Column("disclosed_late_fee", sa.Numeric(14, 2), nullable=False),
        sa.Column("disclosed_rollover_fee", sa.Numeric(14, 2), nullable=False),
        sa.Column("effective_cost_amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("effective_cost_percent", sa.Numeric(12, 4), nullable=False),
        sa.Column("known_cost_amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("unexplained_cost_amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("observation_hash", name="uq_loan_term_observation_hash"),
    )
    for column in (
        "app_id",
        "institution_id",
        "observation_hash",
        "source_type",
        "source_provider",
        "observed_at",
        "currency",
        "created_at",
    ):
        op.create_index(
            f"ix_loan_term_observations_{column}",
            "loan_term_observations",
            [column],
        )


def downgrade() -> None:
    op.drop_table("loan_term_observations")
