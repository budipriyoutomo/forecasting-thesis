"""v3.3: loop kapasitas gudang → adjust SS & Buffer per run (Fase 11.17, 19 Nov 2026)

- Tabel baru `capacity_adjustments` (append-only per run × material; source suggested |
  custom | reset). Cascade bila run/material dihapus.
- `reorder_recommendations`: nilai SS & Buffer sistem sebelum adjust, α efektif, sumber
  adjust. Semua NULLABLE — baris lama = tidak di-adjust.
Additive, tidak mengubah data yang ada.

Revision ID: b1c2d3e4f5a6
Revises: a0b1c2d3e4f5
"""
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b1c2d3e4f5a6"
down_revision: Union[str, None] = "a0b1c2d3e4f5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "capacity_adjustments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "run_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("forecast_runs.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column(
            "material_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("materials.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source", sa.String(10), nullable=False),
        sa.Column("service_level_pct", sa.Numeric(6, 3), nullable=True),
        sa.Column("safety_stock", sa.Numeric(18, 4), nullable=True),
        sa.Column("buffer_stock", sa.Numeric(18, 4), nullable=True),
        sa.Column("previous_value", postgresql.JSONB(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("source IN ('suggested', 'custom', 'reset')", name="ck_capacity_adjustments_source"),
    )
    op.create_index("ix_capacity_adjustments_run_id", "capacity_adjustments", ["run_id"])
    op.create_index("ix_capacity_adjustments_material_id", "capacity_adjustments", ["material_id"])

    op.add_column("reorder_recommendations", sa.Column("safety_stock_system", sa.Numeric(18, 4), nullable=True))
    op.add_column("reorder_recommendations", sa.Column("buffer_stock_system", sa.Numeric(18, 4), nullable=True))
    op.add_column("reorder_recommendations", sa.Column("service_level_effective", sa.Numeric(9, 4), nullable=True))
    op.add_column("reorder_recommendations", sa.Column("adjustment_source", sa.String(10), nullable=True))


def downgrade() -> None:
    op.drop_column("reorder_recommendations", "adjustment_source")
    op.drop_column("reorder_recommendations", "service_level_effective")
    op.drop_column("reorder_recommendations", "buffer_stock_system")
    op.drop_column("reorder_recommendations", "safety_stock_system")
    op.drop_index("ix_capacity_adjustments_material_id", table_name="capacity_adjustments")
    op.drop_index("ix_capacity_adjustments_run_id", table_name="capacity_adjustments")
    op.drop_table("capacity_adjustments")
