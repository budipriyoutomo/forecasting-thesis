"""v3.0 Fase 5: material_requirements + reorder buffer/EOQ/cost

Additive: tabel baru material_requirements (breakdown BOM) + kolom baru nullable di
reorder_recommendations (buffer_stock, eoq_qty, ordering_cost, holding_cost,
total_inventory_cost). Tidak menyentuh data lama.

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
"""
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, None] = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "material_requirements",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("run_id", UUID(as_uuid=True), sa.ForeignKey("forecast_runs.id"), nullable=False),
        sa.Column("material_id", UUID(as_uuid=True), sa.ForeignKey("materials.id"), nullable=False),
        sa.Column("forecast_qty", sa.Numeric(18, 4), nullable=False),
        sa.Column("standard_usage_qty", sa.Numeric(18, 4), nullable=True),
        sa.Column("actual_usage_qty", sa.Numeric(18, 4), nullable=True),
        sa.Column("buffer_stock_pct", sa.Numeric(18, 4), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_material_requirements_run_id", "material_requirements", ["run_id"])
    op.create_index("ix_material_requirements_material_id", "material_requirements", ["material_id"])

    for col in ("buffer_stock", "eoq_qty", "ordering_cost", "holding_cost", "total_inventory_cost"):
        op.add_column("reorder_recommendations", sa.Column(col, sa.Numeric(18, 4), nullable=True))


def downgrade() -> None:
    for col in ("total_inventory_cost", "holding_cost", "ordering_cost", "eoq_qty", "buffer_stock"):
        op.drop_column("reorder_recommendations", col)
    op.drop_index("ix_material_requirements_material_id", table_name="material_requirements")
    op.drop_index("ix_material_requirements_run_id", table_name="material_requirements")
    op.drop_table("material_requirements")
