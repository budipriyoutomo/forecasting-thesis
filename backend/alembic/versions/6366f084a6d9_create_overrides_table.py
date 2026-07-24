"""create overrides table

Revision ID: 6366f084a6d9
Revises: 8e5cdd610f80
Create Date: 2026-07-24

Fase 6 — tabel `overrides` (append-only audit trail, docs/ARCHITECTURE.md §4).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "6366f084a6d9"
down_revision: Union[str, None] = "8e5cdd610f80"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "overrides",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column("target_type", sa.String(length=20), nullable=False),
        sa.Column("target_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("previous_value", postgresql.JSONB(), nullable=True),
        sa.Column("new_value", postgresql.JSONB(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_overrides_target_id", "overrides", ["target_id"])
    op.create_index("ix_overrides_user_id", "overrides", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_overrides_user_id", table_name="overrides")
    op.drop_index("ix_overrides_target_id", table_name="overrides")
    op.drop_table("overrides")
