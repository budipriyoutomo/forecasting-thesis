"""v3.2 Fase 11.1: pemakaian aktual material (buffer stock) + reorder.waste_factor

REVISI_V2 §3.8 / Keputusan #8: buffer = max(0, Σaktual/Σstandar − 1) × kebutuhan periode.
material_usage_history net-new; reorder_recommendations.waste_factor additive.
Dua partial unique index: satu baris per (material, [produk], periode).

Revision ID: a8b9c0d1e2f3
Revises: f7a8b9c0d1e2
"""
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a8b9c0d1e2f3"
down_revision: Union[str, None] = "f7a8b9c0d1e2"
branch_labels = None
depends_on = None

_UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "material_usage_history",
        sa.Column("id", _UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("material_id", _UUID, sa.ForeignKey("materials.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_id", _UUID, sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=True),
        sa.Column("period", sa.Date(), nullable=False),
        sa.Column("production_output", sa.Numeric(18, 4), nullable=True),
        sa.Column("standard_usage", sa.Numeric(18, 4), nullable=False),
        sa.Column("actual_usage", sa.Numeric(18, 4), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("standard_usage >= 0 AND actual_usage >= 0", name="ck_material_usage_non_negative"),
    )
    op.create_index("ix_material_usage_history_material_id", "material_usage_history", ["material_id"])
    op.create_index(
        "uq_material_usage_no_product", "material_usage_history", ["material_id", "period"],
        unique=True, postgresql_where=sa.text("product_id IS NULL"),
    )
    op.create_index(
        "uq_material_usage_product", "material_usage_history", ["material_id", "product_id", "period"],
        unique=True, postgresql_where=sa.text("product_id IS NOT NULL"),
    )
    op.add_column("reorder_recommendations", sa.Column("waste_factor", sa.Numeric(18, 6), nullable=True))


def downgrade() -> None:
    op.drop_column("reorder_recommendations", "waste_factor")
    op.drop_index("uq_material_usage_product", table_name="material_usage_history")
    op.drop_index("uq_material_usage_no_product", table_name="material_usage_history")
    op.drop_index("ix_material_usage_history_material_id", table_name="material_usage_history")
    op.drop_table("material_usage_history")
