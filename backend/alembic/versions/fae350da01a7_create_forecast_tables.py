"""create forecast_runs and forecast_results tables

Revision ID: fae350da01a7
Revises: 9a85016d7be7
Create Date: 2026-07-24

Fase 4 — tabel `forecast_runs` & `forecast_results` (docs/ARCHITECTURE.md §4).
`forecast_results.status` ditambahkan sesuai §8 (RECONCILIATION #15).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "fae350da01a7"
down_revision: Union[str, None] = "9a85016d7be7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "forecast_runs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("horizon", sa.Integer(), nullable=False),
        sa.Column("horizon_unit", sa.String(length=10), nullable=False, server_default="days"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="PENDING"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_forecast_runs_user_id", "forecast_runs", ["user_id"])

    op.create_table(
        "forecast_results",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("forecast_runs.id"), nullable=False),
        sa.Column("material_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("materials.id"), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="COMPLETED"),
        sa.Column("data_profile", postgresql.JSONB(), nullable=True),
        sa.Column("method_used", sa.String(length=20), nullable=True),
        sa.Column("selection_mode", sa.String(length=10), nullable=True),
        sa.Column("mase", sa.Numeric(18, 6), nullable=True),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("forecast_data", postgresql.JSONB(), nullable=True),
        sa.Column("metrics", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_forecast_results_run_id", "forecast_results", ["run_id"])
    op.create_index("ix_forecast_results_material_id", "forecast_results", ["material_id"])


def downgrade() -> None:
    op.drop_index("ix_forecast_results_material_id", table_name="forecast_results")
    op.drop_index("ix_forecast_results_run_id", table_name="forecast_results")
    op.drop_table("forecast_results")
    op.drop_index("ix_forecast_runs_user_id", table_name="forecast_runs")
    op.drop_table("forecast_runs")
