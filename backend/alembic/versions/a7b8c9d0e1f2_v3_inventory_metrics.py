"""v3.0 Fase 7: inventory_metrics (service level, fill rate, stock out, turnover)

Net-new: evaluasi kinerja inventory per run, kolom `scope` (baseline/forecastiq)
memisahkan kinerja EXISTING vs ForecastIQ (RECONCILIATION §Fase 7).

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
"""
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "a7b8c9d0e1f2"
down_revision: Union[str, None] = "f6a7b8c9d0e1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "inventory_metrics",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("run_id", UUID(as_uuid=True), sa.ForeignKey("forecast_runs.id"), nullable=False),
        sa.Column("target_type", sa.String(20), nullable=False),
        sa.Column("target_id", UUID(as_uuid=True), nullable=False),
        sa.Column("scope", sa.String(20), nullable=False, server_default="baseline"),
        sa.Column("service_level", sa.Numeric(9, 4), nullable=False),
        sa.Column("fill_rate", sa.Numeric(9, 4), nullable=False),
        sa.Column("stock_out_rate", sa.Numeric(9, 4), nullable=False),
        sa.Column("inventory_turnover", sa.Numeric(18, 4), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_inventory_metrics_run_id", "inventory_metrics", ["run_id"])


def downgrade() -> None:
    op.drop_index("ix_inventory_metrics_run_id", table_name="inventory_metrics")
    op.drop_table("inventory_metrics")
