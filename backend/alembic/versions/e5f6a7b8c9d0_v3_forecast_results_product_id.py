"""v3.0 swap: forecast_results.product_id + material_id nullable

Additive: forecasting v3.0 berbasis produk jadi. Tambah `product_id` (FK products,
nullable) dan longgarkan `material_id` jadi nullable (jalur legacy v2.0 dipertahankan
sampai cutover Fase 9).

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
"""
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, None] = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "forecast_results",
        sa.Column("product_id", UUID(as_uuid=True), sa.ForeignKey("products.id"), nullable=True),
    )
    op.create_index("ix_forecast_results_product_id", "forecast_results", ["product_id"])
    op.alter_column("forecast_results", "material_id", existing_type=UUID(as_uuid=True), nullable=True)


def downgrade() -> None:
    op.alter_column("forecast_results", "material_id", existing_type=UUID(as_uuid=True), nullable=False)
    op.drop_index("ix_forecast_results_product_id", table_name="forecast_results")
    op.drop_column("forecast_results", "product_id")
