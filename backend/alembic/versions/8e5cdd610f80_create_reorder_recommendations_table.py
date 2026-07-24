"""create reorder_recommendations table

Revision ID: 8e5cdd610f80
Revises: fae350da01a7
Create Date: 2026-07-24

Fase 5 — tabel `reorder_recommendations` (docs/ARCHITECTURE.md §4).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "8e5cdd610f80"
down_revision: Union[str, None] = "fae350da01a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "reorder_recommendations",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("forecast_runs.id"), nullable=False),
        sa.Column("material_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("materials.id"), nullable=False),
        sa.Column("safety_stock", sa.Numeric(18, 4), nullable=False),
        sa.Column("reorder_point", sa.Numeric(18, 4), nullable=False),
        sa.Column("recommended_order_qty", sa.Numeric(18, 4), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_reorder_recommendations_run_id", "reorder_recommendations", ["run_id"])
    op.create_index("ix_reorder_recommendations_material_id", "reorder_recommendations", ["material_id"])


def downgrade() -> None:
    op.drop_index("ix_reorder_recommendations_material_id", table_name="reorder_recommendations")
    op.drop_index("ix_reorder_recommendations_run_id", table_name="reorder_recommendations")
    op.drop_table("reorder_recommendations")
