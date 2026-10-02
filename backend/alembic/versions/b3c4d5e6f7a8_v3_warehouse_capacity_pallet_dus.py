"""v3.0 Fase 10: input kapasitas gudang pallet / dus / kombinasi

Kolom baru di `warehouse_config`: `capacity_mode`, `pallet_qty`, `dus_qty`,
`dus_per_pallet`, `pcs_per_dus`. `capacity_qty` & `uom` tetap ada tapi kini turunan
server (warehouse_service.compute_effective_capacity) — RECONCILIATION
§"Konsolidasi Master Data" (2 Oktober 2026).

Backfill non-destruktif: baris lama → mode DUS, `dus_qty = capacity_qty`; bila unit
produk bukan dus-like, `pcs_per_dus = 1` → `capacity_qty` hasil hitung ulang identik
dengan nilai lama. `uom` diselaraskan ke `products.unit` (capacity_qty memang selalu
dalam unit produk sejak redesain 24 Agustus 2026).

Revision ID: b3c4d5e6f7a8
Revises: a2b3c4d5e6f7
"""
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "b3c4d5e6f7a8"
down_revision: Union[str, None] = "a2b3c4d5e6f7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "warehouse_config",
        sa.Column("capacity_mode", sa.String(10), nullable=False, server_default="DUS"),
    )
    op.add_column(
        "warehouse_config",
        sa.Column("pallet_qty", sa.Numeric(18, 4), nullable=False, server_default="0"),
    )
    op.add_column(
        "warehouse_config",
        sa.Column("dus_qty", sa.Numeric(18, 4), nullable=False, server_default="0"),
    )
    op.add_column("warehouse_config", sa.Column("dus_per_pallet", sa.Numeric(18, 4), nullable=True))
    op.add_column("warehouse_config", sa.Column("pcs_per_dus", sa.Numeric(18, 4), nullable=True))

    op.execute(
        """
        UPDATE warehouse_config wc
        SET dus_qty = wc.capacity_qty,
            uom = p.unit,
            pcs_per_dus = CASE
                WHEN UPPER(TRIM(p.unit)) IN ('DUS', 'KARTON', 'BOX', 'CTN') THEN NULL
                ELSE 1
            END
        FROM products p
        WHERE p.id = wc.product_id
        """
    )

    op.alter_column("warehouse_config", "capacity_mode", server_default=None)
    op.alter_column("warehouse_config", "pallet_qty", server_default=None)
    op.alter_column("warehouse_config", "dus_qty", server_default=None)


def downgrade() -> None:
    # capacity_qty tetap tersimpan → validasi lama tetap jalan setelah downgrade.
    op.drop_column("warehouse_config", "pcs_per_dus")
    op.drop_column("warehouse_config", "dus_per_pallet")
    op.drop_column("warehouse_config", "dus_qty")
    op.drop_column("warehouse_config", "pallet_qty")
    op.drop_column("warehouse_config", "capacity_mode")
