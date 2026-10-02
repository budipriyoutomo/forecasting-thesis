"""v3.0 Fase 10: master template biaya (cost_templates + cost_template_items)

S (`ordering_cost`) & H (`holding_cost`, manual) untuk EOQ/TIC bila template aktif;
overhead & aset penyimpanan hanya referensi saran H. Maksimal satu template aktif
dijaga partial unique index. RECONCILIATION §"Konsolidasi Master Data" (2 Oktober 2026).
Net-new, tanpa backfill — tanpa template aktif EOQ tetap memakai env (perilaku lama).

Revision ID: d5e6f7a8b9c0
Revises: c4d5e6f7a8b9
"""
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d5e6f7a8b9c0"
down_revision: Union[str, None] = "c4d5e6f7a8b9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cost_templates",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("ordering_cost", sa.Numeric(18, 4), nullable=False),
        sa.Column("holding_cost", sa.Numeric(18, 4), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index(
        "uq_cost_templates_single_active",
        "cost_templates",
        ["is_active"],
        unique=True,
        postgresql_where=sa.text("is_active"),
    )

    op.create_table(
        "cost_template_items",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "template_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("cost_templates.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("item_type", sa.String(20), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("monthly_amount", sa.Numeric(18, 4), nullable=True),
        sa.Column("purchase_price", sa.Numeric(18, 4), nullable=True),
        sa.Column("salvage_value", sa.Numeric(18, 4), nullable=True),
        sa.Column("useful_life_months", sa.Integer(), nullable=True),
        sa.Column("qty", sa.Numeric(18, 4), nullable=False, server_default="1"),
        sa.CheckConstraint("item_type IN ('OVERHEAD', 'STORAGE_ASSET')", name="ck_cost_template_items_type"),
    )
    op.create_index("ix_cost_template_items_template_id", "cost_template_items", ["template_id"])


def downgrade() -> None:
    op.drop_index("ix_cost_template_items_template_id", table_name="cost_template_items")
    op.drop_table("cost_template_items")
    op.drop_index("uq_cost_templates_single_active", table_name="cost_templates")
    op.drop_table("cost_templates")
