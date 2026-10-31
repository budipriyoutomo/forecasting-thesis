"""v3.2 Fase 11.2b: master data variabel eksternal + nilai per periode

Keputusan #7 (docs/REVISI_V2.md §6.1): variabel dinamis (musim, cuaca, harga, promo,
event, ...) dengan toggle aktif; nilai per periode, product_id NULL = global. Dua
partial unique index menjaga satu nilai per (variabel, [produk], periode). Net-new.

Revision ID: f7a8b9c0d1e2
Revises: e6f7a8b9c0d1
"""
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f7a8b9c0d1e2"
down_revision: Union[str, None] = "e6f7a8b9c0d1"
branch_labels = None
depends_on = None

_UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "external_variables",
        sa.Column("id", _UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("code", sa.String(50), nullable=False, unique=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("value_type", sa.String(10), nullable=False, server_default="numeric"),
        sa.Column("scope", sa.String(10), nullable=False, server_default="global"),
        sa.Column("unit", sa.String(20), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("value_type IN ('numeric', 'flag')", name="ck_external_variables_value_type"),
        sa.CheckConstraint("scope IN ('global', 'product')", name="ck_external_variables_scope"),
    )
    op.create_table(
        "external_variable_values",
        sa.Column("id", _UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("variable_id", _UUID, sa.ForeignKey("external_variables.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_id", _UUID, sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=True),
        sa.Column("period", sa.Date(), nullable=False),
        sa.Column("value", sa.Numeric(18, 4), nullable=False),
    )
    op.create_index("ix_external_variable_values_variable_id", "external_variable_values", ["variable_id"])
    op.create_index("ix_external_variable_values_product_id", "external_variable_values", ["product_id"])
    op.create_index(
        "uq_external_variable_values_global", "external_variable_values", ["variable_id", "period"],
        unique=True, postgresql_where=sa.text("product_id IS NULL"),
    )
    op.create_index(
        "uq_external_variable_values_product", "external_variable_values", ["variable_id", "product_id", "period"],
        unique=True, postgresql_where=sa.text("product_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_external_variable_values_product", table_name="external_variable_values")
    op.drop_index("uq_external_variable_values_global", table_name="external_variable_values")
    op.drop_index("ix_external_variable_values_product_id", table_name="external_variable_values")
    op.drop_index("ix_external_variable_values_variable_id", table_name="external_variable_values")
    op.drop_table("external_variable_values")
    op.drop_table("external_variables")
