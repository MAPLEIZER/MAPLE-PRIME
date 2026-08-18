"""add privacy-minimized mobile telemetry

Revision ID: 0003_mobile_telemetry
Revises: 0002_reconciliation_findings
"""

import sqlalchemy as sa
from alembic import op

revision = "0003_mobile_telemetry"
down_revision = "0002_reconciliation_findings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "mobile_telemetry_events",
        sa.Column("id", sa.String(80), primary_key=True),
        sa.Column("client_hash", sa.String(64), nullable=False),
        sa.Column("source_kind", sa.String(40), nullable=False),
        sa.Column("app_version", sa.String(80), nullable=False),
        sa.Column("model_version", sa.String(80), nullable=False),
        sa.Column("predicted_label", sa.String(80), nullable=False),
        sa.Column("server_label", sa.String(80), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("user_label", sa.String(80), nullable=True),
        sa.Column("features_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_mobile_telemetry_events_client_hash", "mobile_telemetry_events", ["client_hash"])
    op.create_index("ix_mobile_telemetry_events_predicted_label", "mobile_telemetry_events", ["predicted_label"])
    op.create_index("ix_mobile_telemetry_events_user_label", "mobile_telemetry_events", ["user_label"])
    op.create_index("ix_mobile_telemetry_events_created_at", "mobile_telemetry_events", ["created_at"])


def downgrade() -> None:
    op.drop_table("mobile_telemetry_events")
