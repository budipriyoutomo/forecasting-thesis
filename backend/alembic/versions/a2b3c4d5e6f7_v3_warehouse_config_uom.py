"""v3.0: tambah kolom uom (free input) di warehouse_config

`uom` adalah teks bebas isian planner (mis. "Dus", "Pcs", "Karton") — TIDAK ada
tabel master UOM (keputusan user, redesain 24 Agustus 2026). Baris existing
diisi server_default 'unit' agar kolom bisa NOT NULL tanpa backfill manual;
insert baru wajib isi eksplisit lewat WarehouseConfigCreate (app-layer).

Revision ID: a2b3c4d5e6f7
Revises: e1f2a3b4c5d6
"""
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "a2b3c4d5e6f7"
down_revision: Union[str, None] = "e1f2a3b4c5d6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "warehouse_config",
        sa.Column("uom", sa.String(50), nullable=False, server_default="unit"),
    )
    op.alter_column("warehouse_config", "uom", server_default=None)


def downgrade() -> None:
    op.drop_column("warehouse_config", "uom")
