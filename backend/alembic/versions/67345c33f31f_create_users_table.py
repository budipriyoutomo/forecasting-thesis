"""create users table

Revision ID: 67345c33f31f
Revises:
Create Date: 2026-07-24

Fase 1 — tabel `users` (docs/ARCHITECTURE.md §4). Ditulis manual (bukan
autogenerate) karena DB Supabase belum tentu tersedia saat pengembangan.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "67345c33f31f"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # pgcrypto menyediakan gen_random_uuid(); di Supabase umumnya sudah aktif,
    # tapi dibuat idempotent agar migrasi tetap jalan di Postgres polos.
    op.execute('CREATE EXTENSION IF NOT EXISTS pgcrypto')

    op.create_table(
        "users",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False, server_default="viewer"),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_unique_constraint("uq_users_email", "users", ["email"])
    op.create_index("ix_users_email", "users", ["email"])


def downgrade() -> None:
    op.drop_index("ix_users_email", table_name="users")
    op.drop_constraint("uq_users_email", "users", type_="unique")
    op.drop_table("users")
