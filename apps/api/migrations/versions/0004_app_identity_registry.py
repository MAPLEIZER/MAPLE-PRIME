"""add marketplace app identity registry

Revision ID: 0004_app_identity_registry
Revises: 0003_mobile_telemetry
"""

import sqlalchemy as sa
from alembic import op

revision = "0004_app_identity_registry"
down_revision = "0003_mobile_telemetry"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "marketplace_apps",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("store", sa.String(40), nullable=False),
        sa.Column("package_name", sa.String(255), nullable=False),
        sa.Column("loan_relevance", sa.String(40), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("store", "package_name", name="uq_marketplace_app_package"),
    )
    op.create_index("ix_marketplace_apps_store", "marketplace_apps", ["store"])
    op.create_index("ix_marketplace_apps_package_name", "marketplace_apps", ["package_name"])
    op.create_index("ix_marketplace_apps_loan_relevance", "marketplace_apps", ["loan_relevance"])
    op.create_index("ix_marketplace_apps_first_seen_at", "marketplace_apps", ["first_seen_at"])
    op.create_index("ix_marketplace_apps_last_seen_at", "marketplace_apps", ["last_seen_at"])

    op.create_table(
        "app_store_observations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("app_id", sa.String(36), sa.ForeignKey("marketplace_apps.id", ondelete="CASCADE"), nullable=False),
        sa.Column("observation_hash", sa.String(64), nullable=False),
        sa.Column("source_provider", sa.String(120), nullable=False),
        sa.Column("source_url", sa.String(1000), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("app_name", sa.String(300), nullable=False),
        sa.Column("developer_name", sa.String(300), nullable=False),
        sa.Column("developer_id", sa.String(300), nullable=True),
        sa.Column("support_email", sa.String(320), nullable=True),
        sa.Column("email_domain", sa.String(255), nullable=True),
        sa.Column("developer_website", sa.String(1000), nullable=True),
        sa.Column("developer_domain", sa.String(255), nullable=True),
        sa.Column("privacy_policy_url", sa.String(1000), nullable=True),
        sa.Column("store_url", sa.String(1000), nullable=False),
        sa.Column("category", sa.String(160), nullable=True),
        sa.Column("installs", sa.String(80), nullable=True),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.UniqueConstraint("observation_hash", name="uq_app_store_observation_hash"),
    )
    for column in (
        "app_id",
        "observation_hash",
        "source_provider",
        "observed_at",
        "app_name",
        "developer_name",
        "developer_id",
        "support_email",
        "email_domain",
        "developer_domain",
        "category",
    ):
        op.create_index(f"ix_app_store_observations_{column}", "app_store_observations", [column])

    op.create_table(
        "app_ownership_links",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("app_id", sa.String(36), sa.ForeignKey("marketplace_apps.id", ondelete="CASCADE"), nullable=False),
        sa.Column("institution_id", sa.String(36), sa.ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("signals_json", sa.Text(), nullable=False),
        sa.Column("review_state", sa.String(40), nullable=False),
        sa.Column("reviewed_by", sa.String(120), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("app_id", "institution_id", name="uq_app_ownership_institution"),
    )
    op.create_index("ix_app_ownership_links_app_id", "app_ownership_links", ["app_id"])
    op.create_index("ix_app_ownership_links_institution_id", "app_ownership_links", ["institution_id"])
    op.create_index("ix_app_ownership_links_review_state", "app_ownership_links", ["review_state"])
    op.create_index("ix_app_ownership_links_created_at", "app_ownership_links", ["created_at"])


def downgrade() -> None:
    op.drop_table("app_ownership_links")
    op.drop_table("app_store_observations")
    op.drop_table("marketplace_apps")
