"""v3.2 Fase 11.6: kapasitas gudang per material (polimorfik) + proyeksi stok

Keputusan #1 (produk + material): warehouse_config.item_type (product | material),
product_id jadi NULLABLE, + material_id. Unik per target via partial unique index
(menggantikan unique constraint product_id). Data lama → item_type 'product'.
Net-new stock_projections (tahap 3 thesis, REVISI_V2 §3.3).

Revision ID: e2f3a4b5c6d7
Revises: d1e2f3a4b5c6
"""
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "e2f3a4b5c6d7"
down_revision: Union[str, None] = "d1e2f3a4b5c6"
branch_labels = None
depends_on = None

_UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.add_column("warehouse_config", sa.Column("item_type", sa.String(10), nullable=False, server_default="product"))
    op.add_column(
        "warehouse_config",
        sa.Column("material_id", _UUID, sa.ForeignKey("materials.id", ondelete="CASCADE"), nullable=True),
    )
    op.alter_column("warehouse_config", "product_id", nullable=True)
    op.drop_constraint("uq_warehouse_config_product_id", "warehouse_config", type_="unique")
    op.create_index(
        "uq_warehouse_config_product", "warehouse_config", ["product_id"],
        unique=True, postgresql_where=sa.text("item_type = 'product'"),
    )
    op.create_index(
        "uq_warehouse_config_material", "warehouse_config", ["material_id"],
        unique=True, postgresql_where=sa.text("item_type = 'material'"),
    )
    op.create_index("ix_warehouse_config_material_id", "warehouse_config", ["material_id"])
    op.create_check_constraint(
        "ck_warehouse_config_target",
        "warehouse_config",
        "(item_type = 'product' AND product_id IS NOT NULL AND material_id IS NULL) OR "
        "(item_type = 'material' AND material_id IS NOT NULL AND product_id IS NULL)",
    )

    op.create_table(
        "stock_projections",
        sa.Column("id", _UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("run_id", _UUID, sa.ForeignKey("forecast_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("material_id", _UUID, sa.ForeignKey("materials.id", ondelete="CASCADE"), nullable=False),
        sa.Column("scenario", sa.String(10), nullable=False, server_default="proposed"),
        sa.Column("period", sa.Date(), nullable=False),
        sa.Column("opening_qty", sa.Float(), nullable=False),
        sa.Column("receipt_qty", sa.Float(), nullable=False, server_default="0"),
        sa.Column("usage_qty", sa.Float(), nullable=False),
        sa.Column("order_qty", sa.Float(), nullable=False, server_default="0"),
        sa.Column("ending_qty", sa.Float(), nullable=False),
        sa.Column("shortage_qty", sa.Float(), nullable=False, server_default="0"),
        sa.Column("capacity_qty", sa.Float(), nullable=True),
        sa.Column("utilization_opening_pct", sa.Float(), nullable=True),
        sa.Column("utilization_ending_pct", sa.Float(), nullable=True),
        sa.Column("is_within_capacity", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("scenario IN ('proposed', 'baseline')", name="ck_stock_projections_scenario"),
    )
    op.create_index("ix_stock_projections_run_id", "stock_projections", ["run_id"])


def downgrade() -> None:
    op.drop_index("ix_stock_projections_run_id", table_name="stock_projections")
    op.drop_table("stock_projections")
    op.drop_constraint("ck_warehouse_config_target", "warehouse_config", type_="check")
    op.drop_index("ix_warehouse_config_material_id", table_name="warehouse_config")
    op.drop_index("uq_warehouse_config_material", table_name="warehouse_config")
    op.drop_index("uq_warehouse_config_product", table_name="warehouse_config")
    # Kapasitas material hilang saat downgrade (tak bisa direpresentasikan skema lama).
    op.execute("DELETE FROM warehouse_config WHERE item_type = 'material'")
    op.create_unique_constraint("uq_warehouse_config_product_id", "warehouse_config", ["product_id"])
    op.alter_column("warehouse_config", "product_id", nullable=False)
    op.drop_column("warehouse_config", "material_id")
    op.drop_column("warehouse_config", "item_type")
