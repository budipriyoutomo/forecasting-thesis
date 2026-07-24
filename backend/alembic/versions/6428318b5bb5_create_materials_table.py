"""create materials table

Revision ID: 6428318b5bb5
Revises: 67345c33f31f
Create Date: 2026-07-24

Fase 2 — tabel `materials` (docs/ARCHITECTURE.md §4).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "6428318b5bb5"
down_revision: Union[str, None] = "67345c33f31f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "materials",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("unit", sa.String(length=20), nullable=False),
        sa.Column("lead_time_days", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("moq", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("manual_safety_stock", sa.Numeric(18, 4), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_unique_constraint("uq_materials_code", "materials", ["code"])
    op.create_index("ix_materials_code", "materials", ["code"])


def downgrade() -> None:
    op.drop_index("ix_materials_code", table_name="materials")
    op.drop_constraint("uq_materials_code", "materials", type_="unique")
    op.drop_table("materials")
