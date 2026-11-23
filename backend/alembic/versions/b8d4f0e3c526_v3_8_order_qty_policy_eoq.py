"""forecast_settings.order_qty_policy default = eoq (23 Nov 2026, keputusan user)

Qty pembelian material = hasil EOQ (kelipatan EOQ), bukan order-up-to. Server default diganti
dan baris pengaturan yang ada di-set ke `eoq` atas permintaan eksplisit user ("ya" untuk
menjadikan EOQ default). Admin tetap bisa memilih order-up-to lagi di Pengaturan Forecast.
Rekomendasi reorder yang SUDAH tersimpan tidak diubah (`order_qty_policy_used` = audit);
berlaku saat perencanaan dijalankan ulang.

Revision ID: b8d4f0e3c526
Revises: a7c3e9d2b415
"""
from typing import Union

from alembic import op

revision: str = "b8d4f0e3c526"
down_revision: Union[str, None] = "a7c3e9d2b415"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("forecast_settings", "order_qty_policy", server_default="eoq")
    op.execute("UPDATE forecast_settings SET order_qty_policy = 'eoq' WHERE order_qty_policy = 'order_up_to'")


def downgrade() -> None:
    # Nilai pengaturan sebelum upgrade tidak diketahui — hanya server default yang dikembalikan.
    op.alter_column("forecast_settings", "order_qty_policy", server_default="order_up_to")
