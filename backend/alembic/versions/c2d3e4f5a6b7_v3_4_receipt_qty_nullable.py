"""v3.4: stock_projections.receipt_qty nullable — kedatangan = hasil ROP (20 Nov 2026)

Input kedatangan manual / upload (`material_receipts`) dihapus dari aplikasi; kedatangan =
pesanan hasil ROP (`order_qty`, tiba di periode yang sama). `receipt_qty` dibiarkan ada tapi
NULL untuk proyeksi baru (deprecated). Tabel `material_receipts` TIDAK di-drop (data lama
dipertahankan). Lihat RECONCILIATION §"Kedatangan Material = Hasil Hitungan ROP".

Downgrade: NULL → 0, lalu kembali NOT NULL dengan server default 0.

Revision ID: c2d3e4f5a6b7
Revises: b1c2d3e4f5a6
"""
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "c2d3e4f5a6b7"
down_revision: Union[str, None] = "b1c2d3e4f5a6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "stock_projections", "receipt_qty", existing_type=sa.Float(), nullable=True, server_default=None
    )


def downgrade() -> None:
    op.execute("UPDATE stock_projections SET receipt_qty = 0 WHERE receipt_qty IS NULL")
    op.alter_column(
        "stock_projections", "receipt_qty", existing_type=sa.Float(), nullable=False, server_default="0"
    )
