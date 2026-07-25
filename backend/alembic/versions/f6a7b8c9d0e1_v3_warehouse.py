"""v3.0 Fase 6: warehouse_config + warehouse_validations

Net-new (khas judul thesis): parameter kapasitas gudang & hasil validasi per run.

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
"""
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "f6a7b8c9d0e1"
down_revision: Union[str, None] = "e5f6a7b8c9d0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "warehouse_config",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("warehouse_area_m2", sa.Numeric(18, 4), nullable=False),
        sa.Column("pallet_dimension", JSONB(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_unique_constraint("uq_warehouse_config_category", "warehouse_config", ["category"])

    op.create_table(
        "warehouse_validations",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("run_id", UUID(as_uuid=True), sa.ForeignKey("forecast_runs.id"), nullable=False),
        sa.Column("total_pallet_capacity", sa.Numeric(18, 4), nullable=False),
        sa.Column("total_pallet_required", sa.Numeric(18, 4), nullable=False),
        sa.Column("is_within_capacity", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_warehouse_validations_run_id", "warehouse_validations", ["run_id"])


def downgrade() -> None:
    op.drop_index("ix_warehouse_validations_run_id", table_name="warehouse_validations")
    op.drop_table("warehouse_validations")
    op.drop_constraint("uq_warehouse_config_category", "warehouse_config", type_="unique")
    op.drop_table("warehouse_config")
