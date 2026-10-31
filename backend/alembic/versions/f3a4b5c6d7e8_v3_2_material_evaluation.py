"""v3.2 Fase 11.7: evaluasi inventory material — inventory_days & shortage_cost

REVISI_V2 §3.9: inventory turnover (hari) & biaya kekurangan (qty tak terpenuhi × harga
jual produk). Additive, nullable. target_type 'material' sudah didukung kolom polimorfik.

Revision ID: f3a4b5c6d7e8
Revises: e2f3a4b5c6d7
"""
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "f3a4b5c6d7e8"
down_revision: Union[str, None] = "e2f3a4b5c6d7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("inventory_metrics", sa.Column("inventory_days", sa.Numeric(18, 4), nullable=True))
    op.add_column("inventory_metrics", sa.Column("shortage_cost", sa.Numeric(18, 4), nullable=True))


def downgrade() -> None:
    op.drop_column("inventory_metrics", "shortage_cost")
    op.drop_column("inventory_metrics", "inventory_days")
