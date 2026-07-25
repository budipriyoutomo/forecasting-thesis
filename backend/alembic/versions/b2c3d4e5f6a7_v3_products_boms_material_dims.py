"""v3.0 Fase 2: products, boms + materials dimension/qty_per_pallet

Additive (strategi migrasi §0): tabel baru products & boms, kolom baru nullable di
materials. Tidak menyentuh data lama.

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
"""
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "products",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("unit", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_unique_constraint("uq_products_code", "products", ["code"])
    op.create_index("ix_products_code", "products", ["code"])

    op.create_table(
        "boms",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("product_id", UUID(as_uuid=True), sa.ForeignKey("products.id"), nullable=False),
        sa.Column("material_id", UUID(as_uuid=True), sa.ForeignKey("materials.id"), nullable=False),
        sa.Column("qty_per_unit", sa.Numeric(18, 6), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_boms_product_id", "boms", ["product_id"])
    op.create_index("ix_boms_material_id", "boms", ["material_id"])

    op.add_column("materials", sa.Column("dimension", JSONB(), nullable=True))
    op.add_column("materials", sa.Column("qty_per_pallet", sa.Numeric(18, 4), nullable=True))


def downgrade() -> None:
    op.drop_column("materials", "qty_per_pallet")
    op.drop_column("materials", "dimension")
    op.drop_index("ix_boms_material_id", table_name="boms")
    op.drop_index("ix_boms_product_id", table_name="boms")
    op.drop_table("boms")
    op.drop_index("ix_products_code", table_name="products")
    op.drop_constraint("uq_products_code", "products", type_="unique")
    op.drop_table("products")
