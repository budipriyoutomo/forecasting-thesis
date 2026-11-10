"""v3.3: produk hanya punya satu harga — hapus `products.cost_price` (HPP)

Keputusan user 10 Nov 2026 (RECONCILIATION §"Satu harga produk"): HPP tidak dipakai di
perhitungan apa pun (hanya pembanding di ringkasan biaya BOM), jadi produk cukup punya satu
harga = `selling_price` ("Harga produk"). Nilai HPP TIDAK disalin ke `selling_price` —
keduanya bermakna beda (shortage cost memakai harga jual).

Downgrade menambah kolom kembali sebagai NULL (nilai lama tidak bisa dipulihkan).

Revision ID: e8f9a0b1c2d3
Revises: d7e8f9a0b1c2
"""
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "e8f9a0b1c2d3"
down_revision: Union[str, None] = "d7e8f9a0b1c2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("products", "cost_price")


def downgrade() -> None:
    op.add_column("products", sa.Column("cost_price", sa.Numeric(18, 4), nullable=True))
