"""v3.0 Fase 3: demand_history + upload_sessions.n_products_detected

Additive: tabel baru demand_history (3 seri paralel per produk). Kolom
`upload_sessions.n_materials_detected` di-rename jadi `n_products_detected`
(ingestion sekarang berbasis produk jadi). `consumption_history` DIBIARKAN
utuh sampai cutover Fase 9 (strategi migrasi §0).

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
"""
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, None] = "b2c3d4e5f6a7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "demand_history",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("product_code", sa.String(50), nullable=False),
        sa.Column("product_id", UUID(as_uuid=True), sa.ForeignKey("products.id"), nullable=True),
        sa.Column("period", sa.Date(), nullable=False),
        sa.Column("forecast_existing", sa.Numeric(18, 4), nullable=True),
        sa.Column("planning", sa.Numeric(18, 4), nullable=True),
        sa.Column("actual", sa.Numeric(18, 4), nullable=False),
        sa.Column("upload_session_id", UUID(as_uuid=True), sa.ForeignKey("upload_sessions.id"), nullable=False),
    )
    op.create_index("ix_demand_history_product_code", "demand_history", ["product_code"])
    op.create_index("ix_demand_history_product_id", "demand_history", ["product_id"])
    op.create_index("ix_demand_history_upload_session_id", "demand_history", ["upload_session_id"])

    op.alter_column("upload_sessions", "n_materials_detected", new_column_name="n_products_detected")


def downgrade() -> None:
    op.alter_column("upload_sessions", "n_products_detected", new_column_name="n_materials_detected")
    op.drop_index("ix_demand_history_upload_session_id", table_name="demand_history")
    op.drop_index("ix_demand_history_product_id", table_name="demand_history")
    op.drop_index("ix_demand_history_product_code", table_name="demand_history")
    op.drop_table("demand_history")
