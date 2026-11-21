"""v3.7: users.is_active — User Management (21 Nov 2026)

Admin menonaktifkan user lewat halaman User Management (bukan hapus: forecast run / override
menyimpan FK ke users). User nonaktif ditolak saat login (AUTH_ACCOUNT_INACTIVE). Semua user
lama otomatis aktif (server default true). Lihat RECONCILIATION §"User Management — CR v3.7".

Revision ID: d3e4f5a6b7c8
Revises: c2d3e4f5a6b7
"""
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "d3e4f5a6b7c8"
down_revision: Union[str, None] = "c2d3e4f5a6b7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))


def downgrade() -> None:
    op.drop_column("users", "is_active")
