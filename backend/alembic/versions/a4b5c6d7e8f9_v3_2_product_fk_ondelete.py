"""v3.2: FK ke products.id diberi ON DELETE — hapus produk tidak lagi gagal 500

boms & warehouse_config (konfigurasi turunan produk) → CASCADE.
demand_history & forecast_results (histori) → SET NULL; demand_history tetap
menyimpan `product_code` sebagai jejak.

Revision ID: a4b5c6d7e8f9
Revises: f3a4b5c6d7e8
"""
from typing import Union

from alembic import op

revision: str = "a4b5c6d7e8f9"
down_revision: Union[str, None] = "f3a4b5c6d7e8"
branch_labels = None
depends_on = None

# (tabel, ondelete baru) — nama constraint memakai default Postgres `<tabel>_product_id_fkey`.
_FKS = [
    ("boms", "CASCADE"),
    ("warehouse_config", "CASCADE"),
    ("demand_history", "SET NULL"),
    ("forecast_results", "SET NULL"),
]


def _recreate(table: str, ondelete: str | None) -> None:
    name = f"{table}_product_id_fkey"
    op.drop_constraint(name, table, type_="foreignkey")
    op.create_foreign_key(name, table, "products", ["product_id"], ["id"], ondelete=ondelete)


def upgrade() -> None:
    for table, ondelete in _FKS:
        _recreate(table, ondelete)


def downgrade() -> None:
    for table, _ in _FKS:
        _recreate(table, None)
