"""v3.0 Fase 10: harga master data (IDR, opsional)

`materials.unit_price` (harga beli per unit), `products.cost_price` (HPP) dan
`products.selling_price` (harga jual) — semua nullable, additive, tanpa backfill.
RECONCILIATION §"Konsolidasi Master Data" (2 Oktober 2026).

Revision ID: c4d5e6f7a8b9
Revises: b3c4d5e6f7a8
"""
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "c4d5e6f7a8b9"
down_revision: Union[str, None] = "b3c4d5e6f7a8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("materials", sa.Column("unit_price", sa.Numeric(18, 4), nullable=True))
    op.add_column("products", sa.Column("cost_price", sa.Numeric(18, 4), nullable=True))
    op.add_column("products", sa.Column("selling_price", sa.Numeric(18, 4), nullable=True))


def downgrade() -> None:
    op.drop_column("products", "selling_price")
    op.drop_column("products", "cost_price")
    op.drop_column("materials", "unit_price")
